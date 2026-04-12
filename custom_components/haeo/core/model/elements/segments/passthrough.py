"""Passthrough segment — identity transform."""

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
    """Identity segment with no constraints or costs."""

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
        power_in: HighspyArray,
        direction: str = "",
    ) -> None:
        """Initialize passthrough segment."""
        _ = spec
        _ = direction
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            power_in=power_in,
        )


__all__ = ["PassthroughSegment"]
