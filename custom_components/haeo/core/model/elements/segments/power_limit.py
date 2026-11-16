"""Power limit segment — constrains maximum power flow."""

from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; segments only use these via hasattr/isinstance duck typing.
    Literal,
    NotRequired,
)

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import Rows
from custom_components.haeo.core.model.reactive import TrackedParam, constraint
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import FlowProvider, Segment


class PowerLimitSegmentSpec(TypedDict):
    """Specification for creating a PowerLimitSegment.

    Directional fields are resolved by the Connection into `max_power`.
    """

    segment_type: Literal["power_limit"]
    max_power: NotRequired[NDArray[np.float64] | float | None]
    fixed: NotRequired[bool | None]
    control_point: NotRequired[bool]
    """Whether the limit is one the hardware can be set to; False for limits that only model something."""
    # Directional aliases — resolved by Connection, not used by segment directly
    max_power_source_target: NotRequired[NDArray[np.float64] | float | None]
    max_power_target_source: NotRequired[NDArray[np.float64] | float | None]


class PowerLimitSegment(Segment):
    """Constrains maximum power flow."""

    max_power: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Solver,
        *,
        spec: PowerLimitSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize power limit segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            upstream=upstream,
        )
        self._fixed = bool(spec.get("fixed"))
        self._control_point = spec.get("control_point", True)
        self.max_power = broadcast_to_sequence(spec.get("max_power"), self._n_periods)

    @property
    def fixed(self) -> bool:
        """Return whether the flow is held at its max power rather than limited by it."""
        return self._fixed

    @property
    def control_point(self) -> bool:
        """Return whether the limit is one the hardware can be set to, so it can be recommended."""
        return self._control_point

    @constraint(output=True, unit="$/kWh")
    def power_limit(self) -> Rows:
        """Directional power limit constraint (energy-native).

        Formulated as energy: power * dt <= max_power * dt.
        Shadow prices are $/kWh. Without a max power the rows are free, so they
        stay in the LP and can bind later without changing its shape.
        """
        energy = self.total_power_in * self.periods
        if self.max_power is None:
            return energy.free()
        if self._fixed:
            return energy == self.max_power * self.periods
        return energy <= self.max_power * self.periods


__all__ = [
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
]
