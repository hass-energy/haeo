"""Efficiency segment — applies losses to power flow."""

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
    """Applies efficiency losses: output = input * efficiency."""

    efficiency: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

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
        power_in: HighspyArray,
        direction: str,
    ) -> None:
        """Initialize efficiency segment.

        Args:
            spec: Segment specification with directional efficiencies.
            direction: "st" or "ts" — determines which efficiency to use.

        """
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            power_in=power_in,
        )
        if direction == "st":
            self.efficiency = broadcast_to_sequence(spec.get("efficiency_source_target"), self._n_periods)
        else:
            self.efficiency = broadcast_to_sequence(spec.get("efficiency_target_source"), self._n_periods)

    @property
    def power_out(self) -> HighspyArray:
        """Output with efficiency applied."""
        if self.efficiency is None:
            return self._power_in
        return self._power_in * self.efficiency


__all__ = ["EfficiencySegment", "EfficiencySegmentSpec"]
