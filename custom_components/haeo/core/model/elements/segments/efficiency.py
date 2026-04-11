"""Efficiency segment that applies losses to power flow.

Transform: output = input * efficiency.
Returns expressions, not new variables.
"""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment


class EfficiencySegmentSpec(TypedDict):
    """Specification for creating an EfficiencySegment."""

    segment_type: Literal["efficiency"]
    efficiency_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    efficiency_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class EfficiencySegment(Segment):
    """Segment that applies efficiency losses to power flow.

    Transform: output = input * efficiency (an expression, not a new variable).
    """

    efficiency_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    efficiency_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: EfficiencySegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        """Initialize efficiency segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
        )
        self.efficiency_source_target = broadcast_to_sequence(spec.get("efficiency_source_target"), self._n_periods)
        self.efficiency_target_source = broadcast_to_sequence(spec.get("efficiency_target_source"), self._n_periods)

    def apply(self, power_st: HighspyArray, power_ts: HighspyArray) -> tuple[HighspyArray, HighspyArray]:
        """Apply efficiency: output = input * efficiency."""
        self._power_in_st = power_st
        self._power_in_ts = power_ts

        # Apply efficiency as expression (no new variables)
        eff_st = self.efficiency_source_target
        out_st = power_st if eff_st is None else power_st * eff_st

        eff_ts = self.efficiency_target_source
        out_ts = power_ts if eff_ts is None else power_ts * eff_ts

        self._power_out_st = out_st
        self._power_out_ts = out_ts
        return out_st, out_ts


__all__ = ["EfficiencySegment", "EfficiencySegmentSpec"]
