"""Efficiency segment that applies losses to power flow.

Efficiency reduces output power relative to input:
    power_out = power_in * efficiency

This models inverter losses, transformer losses, etc.
"""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray

from .segment import Segment


class EfficiencySegment(Segment):
    """Segment that applies efficiency losses to power flow.

    Uses a single variable per direction with efficiency applied via properties:
        power_out_st = power_in_st * efficiency_st
        power_out_ts = power_in_ts * efficiency_ts

    Efficiency values are fractions in range (0, 1].
    """

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        efficiency_st: NDArray[np.floating[Any]] | None = None,
        efficiency_ts: NDArray[np.floating[Any]] | None = None,
    ) -> None:
        """Initialize efficiency segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            efficiency_st: Efficiency for source→target direction (fraction 0-1).
                          If None, defaults to 1.0 (lossless).
            efficiency_ts: Efficiency for target→source direction (fraction 0-1).
                          If None, defaults to 1.0 (lossless).

        """
        super().__init__(segment_id, n_periods, periods, solver)

        # Store efficiency values
        self._efficiency_st = efficiency_st if efficiency_st is not None else np.ones(n_periods)
        self._efficiency_ts = efficiency_ts if efficiency_ts is not None else np.ones(n_periods)

        # Single variable per direction - efficiency applied via properties
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_st

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction (after efficiency loss)."""
        return self._power_st * self._efficiency_st

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_ts

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction (after efficiency loss)."""
        return self._power_ts * self._efficiency_ts


__all__ = ["EfficiencySegment"]
