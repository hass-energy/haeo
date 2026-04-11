"""Passthrough segment with no constraints or costs.

Identity transform: returns input power unchanged.
"""

from typing import Any, Literal

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element

from .segment import Segment


class PassthroughSegmentSpec(TypedDict):
    """Specification for creating a PassthroughSegment."""

    segment_type: Literal["passthrough"]


class PassthroughSegment(Segment):
    """Lossless segment that passes power through unchanged."""

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: PassthroughSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        """Initialize passthrough segment."""
        _ = spec
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
        )

    def apply(self, power_st: HighspyArray, power_ts: HighspyArray) -> tuple[HighspyArray, HighspyArray]:
        """Identity: return input unchanged."""
        self._power_in_st = self._power_out_st = power_st
        self._power_in_ts = self._power_out_ts = power_ts
        return power_st, power_ts


__all__ = ["PassthroughSegment"]
