"""Level segments: flows set by the difference in level between a connection's ends.

Every network element that has a level exposes it as one expression per
period. A battery's level is affine in its stored energy and a node's level is
a forecast, so the difference between two levels is linear.

The flow reads the level at the end of each period. Draining a store toward its
surroundings then never overshoots them, however long the period, which a flow
read at the start of the period would do once a period is longer than the
store's time constant.
"""

from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here.
    ClassVar,
    Literal,
    Protocol,
    runtime_checkable,
)

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import LinearArray, Rows
from custom_components.haeo.core.model.reactive import TrackedParam, constraint
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import FlowProvider, Segment


@runtime_checkable
class HasLevel(Protocol):
    """An element with a level at the end of each period."""

    @property
    def end_level(self) -> LinearArray:
        """Level at the end of each period."""
        ...


class ConductionSegmentSpec(TypedDict):
    """Specification for creating a ConductionSegment."""

    segment_type: Literal["conduction"]
    conductance: NDArray[np.float64] | float


class LevelLimitSegmentSpec(TypedDict):
    """Specification for creating a LevelLimitSegment."""

    segment_type: Literal["level_limit"]
    conductance: NDArray[np.float64] | float


class LevelSegment(Segment):
    """Base for segments whose flow is bounded by conductance times the level difference of their ends.

    Conductance is power per unit of level difference, such as kW/°C between two
    thermal masses or kW/kWh (one per hour) for a store leaking a share of its energy.
    """

    conductance: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Solver,
        *,
        spec: ConductionSegmentSpec | LevelLimitSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize a level segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            upstream=upstream,
        )
        if not isinstance(source_element, HasLevel) or not isinstance(target_element, HasLevel):
            msg = f"Segment {segment_id} joins {source_element.name} and {target_element.name}, which must have levels"
            raise TypeError(msg)
        self._source_level: HasLevel = source_element
        self._target_level: HasLevel = target_element
        self.conductance = broadcast_to_sequence(spec["conductance"], self._n_periods)

    @property
    def level_flow(self) -> LinearArray:
        """Power the level difference drives from source to target at the end of each period."""
        level_difference = self._source_level.end_level - self._target_level.end_level
        return level_difference * self.conductance


class ConductionSegment(LevelSegment):
    """Fixes the flow at conductance times the level difference, in either direction.

    Models passive transfer the plan cannot control: heat through a wall,
    standing losses to the surroundings, or a battery's self-discharge.
    """

    reversible: ClassVar[bool] = True

    @constraint(output=True, unit="$/kWh")
    def conduction(self) -> Rows:
        """Constraint: energy through the segment equals the energy the level difference drives."""
        return self.total_power_in * self.periods == self.level_flow * self.periods


class LevelLimitSegment(LevelSegment):
    """Caps the flow at conductance times the level difference.

    Models a transfer the plan controls up to a rate its levels allow: a heat
    exchanger coil that delivers less as the store cools toward the water it heats.
    """

    @constraint(output=True, unit="$/kWh")
    def level_limit(self) -> Rows:
        """Constraint: energy through the segment is at most the energy the level difference allows."""
        return self.total_power_in * self.periods <= self.level_flow * self.periods


__all__ = [
    "ConductionSegment",
    "ConductionSegmentSpec",
    "HasLevel",
    "LevelLimitSegment",
    "LevelLimitSegmentSpec",
    "LevelSegment",
]
