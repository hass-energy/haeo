"""Passthrough segment with no constraints or costs.

A simple segment that creates power variables but applies no transformations.
Power in equals power out (lossless).
"""

from typing import Any, Literal

__all__ = ["PassthroughSegment", "PassthroughSegmentSpec"]

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from .segment import Segment


class PassthroughSegmentSpec(TypedDict):
    """Specification for creating a PassthroughSegment."""

    segment_type: Literal["passthrough"]


class PassthroughSegment(Segment):
    """Lossless segment that passes power through unchanged.

    Creates single power variables for each direction (in == out).
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
    ) -> None:
        """Initialize passthrough segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            spec: Passthrough segment specification (unused).

        """
        _ = spec
        super().__init__(segment_id, n_periods, periods, solver)

        # Create single power variable per direction (lossless, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_st

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction (same as in, lossless)."""
        return self._power_st

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_ts

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction (same as in, lossless)."""
        return self._power_ts


__all__ = ["PassthroughSegment"]
