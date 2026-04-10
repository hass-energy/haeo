"""Passthrough segment with no constraints or costs.

A simple segment that passes power through unchanged (lossless).
Power in equals power out per tag.
"""

from typing import Any, Literal

from highspy import Highs
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element

from .segment import Segment


class PassthroughSegmentSpec(TypedDict):
    """Specification for creating a PassthroughSegment."""

    segment_type: Literal["passthrough"]


class PassthroughSegment(Segment):
    """Lossless segment that passes power through unchanged.

    Uses the base class's per-tag variables (lossless: in == out per tag).
    Applies no constraints or costs.
    """

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


__all__ = ["PassthroughSegment"]
