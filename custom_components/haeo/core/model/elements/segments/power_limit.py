"""Power limit segment — constrains maximum power flow."""

from typing import Any, Literal, NotRequired

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
    max_power: NotRequired[NDArray[np.floating[Any]] | float | None]
    fixed: NotRequired[bool | None]
    # Directional aliases — resolved by Connection, not used by segment directly
    max_power_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    max_power_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class PowerLimitSegment(Segment):
    """Constrains maximum power flow."""

    max_power: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: PowerLimitSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        power_in: HighspyArray,
        tag_flows_in: dict[int, HighspyArray] | None = None,
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
            tag_flows_in=tag_flows_in,
        )
        self._fixed = spec.get("fixed", False)
        self.max_power = broadcast_to_sequence(spec.get("max_power"), self._n_periods)

    @constraint(output=True, unit="$/kW")
    def power_limit(self) -> list[highs_linear_expression] | None:
        """Directional power limit constraint."""
        if self.max_power is None:
            return None
        if self._fixed:
            return list(self._power_in == self.max_power)
        return list(self._power_in <= self.max_power)


__all__ = [
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
]
