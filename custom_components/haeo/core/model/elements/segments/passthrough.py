"""Passthrough segment — identity transform."""

from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; segments only use these via hasattr/isinstance duck typing.
    Literal,
)

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
        periods: NDArray[np.float64],
        solver: Highs,
        *,
        spec: PassthroughSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        power_in: dict[int, HighspyArray],
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
            power_in=power_in,
        )


__all__ = ["PassthroughSegment"]
