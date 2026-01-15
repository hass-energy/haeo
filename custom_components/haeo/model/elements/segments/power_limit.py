"""Power limit segment that constrains maximum power flow.

Limits power flow in each direction and optionally prevents simultaneous
bidirectional flow at full capacity (time-slice constraint).
"""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.reactive import TrackedParam, constraint

from .segment import Segment


class PowerLimitSegment(Segment):
    """Segment that limits maximum power flow.

    Creates single power variables for each direction (no losses, so in == out).

    Constraints:
        power_st <= max_power_st  (or == if fixed)
        power_ts <= max_power_ts  (or == if fixed)

    Time-slice constraint (when both limits set):
        (power_st / max_power_st) + (power_ts / max_power_ts) <= 1

    This prevents simultaneous bidirectional flow at full capacity.

    Uses TrackedParam for max_power values to enable warm-start optimization.
    """

    # TrackedParams for warm-start support
    max_power_st: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    max_power_ts: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        max_power_st: NDArray[np.floating[Any]] | None = None,
        max_power_ts: NDArray[np.floating[Any]] | None = None,
        fixed: bool = False,
    ) -> None:
        """Initialize power limit segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            max_power_st: Maximum power for source→target direction (kW per period)
            max_power_ts: Maximum power for target→source direction (kW per period)
            fixed: If True, power is fixed to max values (== instead of <=)

        """
        super().__init__(segment_id, n_periods, periods, solver)
        self._fixed = fixed

        # Create single power variable per direction (lossless segment, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        # Set tracked params (these trigger reactive infrastructure)
        self.max_power_st = max_power_st.astype(np.float64) if max_power_st is not None else None
        self.max_power_ts = max_power_ts.astype(np.float64) if max_power_ts is not None else None

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

    @constraint(output=True, unit="$/kW")
    def power_limit_st(self) -> list[highs_linear_expression] | None:
        """Power limit constraint for source→target direction."""
        if self.max_power_st is None:
            return None

        if self._fixed:
            return list(self._power_st == self.max_power_st)
        return list(self._power_st <= self.max_power_st)

    @constraint(output=True, unit="$/kW")
    def power_limit_ts(self) -> list[highs_linear_expression] | None:
        """Power limit constraint for target→source direction."""
        if self.max_power_ts is None:
            return None

        if self._fixed:
            return list(self._power_ts == self.max_power_ts)
        return list(self._power_ts <= self.max_power_ts)

    @constraint(output=True, unit="$/kW")
    def time_slice(self) -> list[highs_linear_expression] | None:
        """Time-slice constraint: prevent simultaneous bidirectional flow at capacity.

        Constraint: (power_st / max_power_st) + (power_ts / max_power_ts) <= 1
        """
        if self.max_power_st is None or self.max_power_ts is None:
            return None

        # Normalize power to [0, 1] range based on capacity
        # Handle zero capacity by setting coefficient to 0
        coeff_st = np.divide(
            1.0,
            self.max_power_st,
            out=np.zeros(self._n_periods),
            where=self.max_power_st > 0,
        )
        coeff_ts = np.divide(
            1.0,
            self.max_power_ts,
            out=np.zeros(self._n_periods),
            where=self.max_power_ts > 0,
        )

        normalized_st = self._power_st * coeff_st
        normalized_ts = self._power_ts * coeff_ts
        return list(normalized_st + normalized_ts <= 1.0)


__all__ = ["PowerLimitSegment"]
