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
    Final,
    Literal,
    NotRequired,
    Protocol,
    runtime_checkable,
)

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import LinearArray, Rows
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import FlowProvider, Segment

# Price of each kWh a level limit is exceeded, far above any energy price, so the
# cap is only broken when the levels already sit past each other
DEFAULT_VIOLATION_PRICE: Final = 100.0


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
    source_level: NotRequired[NDArray[np.float64] | float | None]
    target_level: NotRequired[NDArray[np.float64] | float | None]


class LevelLimitSegmentSpec(TypedDict):
    """Specification for creating a LevelLimitSegment."""

    segment_type: Literal["level_limit"]
    conductance: NDArray[np.float64] | float
    violation_price: NotRequired[NDArray[np.float64] | float]
    source_level: NotRequired[NDArray[np.float64] | float | None]
    target_level: NotRequired[NDArray[np.float64] | float | None]


def _end_level(element: HasLevel, override: NDArray[np.float64] | None) -> LinearArray:
    """Return an end's level: the level given for it, or the element's own."""
    return element.end_level if override is None else LinearArray.constants(override)


class LevelSegment(Segment):
    """Base for segments whose flow is bounded by conductance times the level difference of their ends.

    Conductance is power per unit of level difference, such as kW/°C between two
    thermal masses or kW/kWh (one per hour) for a store leaking a share of its energy.
    A source or target level, when given, replaces that end's own, such as the
    temperature of the cold water a coil heats on its way to a tap, or of the
    outdoor air a damper lets in.
    """

    conductance: TrackedParam[NDArray[np.float64]] = TrackedParam()
    source_level: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    target_level: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

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
        self.source_level = broadcast_to_sequence(spec.get("source_level"), self._n_periods)
        self.target_level = broadcast_to_sequence(spec.get("target_level"), self._n_periods)

    @property
    def level_flow(self) -> LinearArray:
        """Power the level difference drives from source to target at the end of each period."""
        return (
            _end_level(self._source_level, self.source_level) - _end_level(self._target_level, self.target_level)
        ) * self.conductance


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
    exchanger coil that delivers less as the store cools toward the water it
    heats, or a damper letting in outdoor air.

    A one-way flow with a cap below zero would force the levels apart, such as
    holding a tank above the water it heats. The cap has priced slack instead,
    so a level past the other end costs its violation price rather than making
    the plan infeasible. A period whose conductance is zero has a cap of zero
    and constrains no level, so the direction a flow may run in can be chosen
    per period, from forecasts, before the optimization.
    """

    violation_price: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Solver,
        *,
        spec: LevelLimitSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize a level limit segment and the slack on its cap."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            spec=spec,
            source_element=source_element,
            target_element=target_element,
            upstream=upstream,
        )
        self.violation_price = broadcast_to_sequence(
            spec.get("violation_price", DEFAULT_VIOLATION_PRICE), self._n_periods
        )
        self._over_limit = solver.add_variables(n_periods, name=f"{segment_id}.over_limit")

    @constraint(output=True, unit="$/kWh")
    def level_limit(self) -> Rows:
        """Constraint: energy through the segment is at most the energy the level difference allows, or pays."""
        return self.total_power_in * self.periods <= (self.level_flow + self._over_limit) * self.periods

    @cost
    def level_limit_violation(self) -> LinearArray:
        """Cost: energy over the cap, at the violation price."""
        return (self._over_limit * (self.violation_price * self.periods)).total()


__all__ = [
    "DEFAULT_VIOLATION_PRICE",
    "ConductionSegment",
    "ConductionSegmentSpec",
    "HasLevel",
    "LevelLimitSegment",
    "LevelLimitSegmentSpec",
    "LevelSegment",
]
