"""Power limit segment — constrains maximum power flow."""

from typing import Any, Literal, NotRequired  # noqa: TID251  # legacy Any usage; migrate to precise types

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, constraint
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment


class PowerLimitSegmentSpec(TypedDict):
    """Specification for creating a PowerLimitSegment.

    Directional fields are resolved by the Connection into `max_power`.
    """

    segment_type: Literal["power_limit"]
    max_power: NotRequired[NDArray[np.float64] | float | None]
    fixed: NotRequired[bool | None]
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
        solver: Highs,
        *,
        spec: PowerLimitSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        power_in: dict[int, HighspyArray],
    ) -> None:
        """Initialize power limit segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            power_in=power_in,
        )
        self._fixed = spec.get("fixed", False)
        self.max_power = broadcast_to_sequence(spec.get("max_power"), self._n_periods)

    @constraint(output=True, unit="$/kWh")
    def power_limit(self) -> list[highs_linear_expression] | None:
        """Directional power limit constraint (energy-native).

        Formulated as energy: power * dt <= max_power * dt.
        Shadow prices are $/kWh.
        """
        if self.max_power is None:
            return None
        total = self.total_power_in
        dt = self.periods
        if self._fixed:
            return list(total * dt == self.max_power * dt)
        return list(total * dt <= self.max_power * dt)


__all__ = [
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
]
