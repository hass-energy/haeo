"""Efficiency segment that applies losses to power flow.

Efficiency reduces output power relative to input:
    power_out = power_in * efficiency

This models inverter losses, transformer losses, etc.
"""

from typing import Any, Final, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from .segment import Segment

# Efficiency is specified as percentage (0-100), convert to fraction
EFFICIENCY_PERCENT: Final = 100.0


class EfficiencySegmentSpec(TypedDict):
    """Specification for creating an EfficiencySegment."""

    segment_type: Literal["efficiency"]
    name: NotRequired[str]
    efficiency_source_target: NotRequired[NDArray[np.floating[Any]]]
    efficiency_target_source: NotRequired[NDArray[np.floating[Any]]]


class EfficiencySegment(Segment):
    """Segment that applies efficiency losses to power flow.

    Uses a single variable per direction with efficiency applied via properties:
        power_out_st = power_in_st * efficiency_source_target
        power_out_ts = power_in_ts * efficiency_target_source

    Efficiency values are fractions in range (0, 1].
    """

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        efficiency_source_target: NDArray[np.floating[Any]] | None = None,
        efficiency_target_source: NDArray[np.floating[Any]] | None = None,
    ) -> None:
        """Initialize efficiency segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            efficiency_source_target: Efficiency for source→target direction (fraction 0-1).
                          If None, defaults to 1.0 (lossless).
            efficiency_target_source: Efficiency for target→source direction (fraction 0-1).
                          If None, defaults to 1.0 (lossless).

        """
        super().__init__(segment_id, n_periods, periods, solver)

        # Store efficiency values
        self._efficiency_source_target = self._normalize_efficiency(efficiency_source_target)
        self._efficiency_target_source = self._normalize_efficiency(efficiency_target_source)

        # Single variable per direction - efficiency applied via properties
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_st

    @property
    def efficiency_source_target(self) -> NDArray[np.floating[Any]]:
        """Efficiency for source→target direction."""
        return self._efficiency_source_target

    @efficiency_source_target.setter
    def efficiency_source_target(self, value: NDArray[np.floating[Any]] | float | None) -> None:
        self._efficiency_source_target = self._normalize_efficiency(value)

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction (after efficiency loss)."""
        return self._power_st * self._efficiency_source_target

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_ts

    @property
    def efficiency_target_source(self) -> NDArray[np.floating[Any]]:
        """Efficiency for target→source direction."""
        return self._efficiency_target_source

    @efficiency_target_source.setter
    def efficiency_target_source(self, value: NDArray[np.floating[Any]] | float | None) -> None:
        self._efficiency_target_source = self._normalize_efficiency(value)

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction (after efficiency loss)."""
        return self._power_ts * self._efficiency_target_source

    def _normalize_efficiency(self, value: NDArray[np.floating[Any]] | float | None) -> NDArray[np.float64]:
        """Normalize efficiency to a period-length float array."""
        if value is None:
            return np.ones(self._n_periods, dtype=np.float64)
        arr = np.asarray(value, dtype=np.float64)
        if arr.shape == ():
            return np.full(self._n_periods, float(arr), dtype=np.float64)
        if arr.shape != (self._n_periods,):
            msg = f"Expected length {self._n_periods} for {self.segment_id!r}, got {arr.shape}"
            raise ValueError(msg)
        return arr


__all__ = ["EFFICIENCY_PERCENT", "EfficiencySegment", "EfficiencySegmentSpec"]
