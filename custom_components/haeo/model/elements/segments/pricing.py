"""Pricing segment that adds transfer costs to the objective.

Adds cost proportional to power flow:
    cost = power * price * period_duration
"""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.reactive import TrackedParam, cost

from .segment import Segment


class PricingSegment(Segment):
    """Segment that adds transfer pricing costs.

    Creates single power variables for each direction (lossless, in == out).

    Cost contribution:
        cost_st = sum(power_st * price_st * periods)
        cost_ts = sum(power_ts * price_ts * periods)

    Prices are in $/kWh, power in kW, periods in hours.

    Uses TrackedParam for prices to enable warm-start optimization.
    """

    # TrackedParams for warm-start support
    price_st: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    price_ts: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        price_st: NDArray[np.floating[Any]] | None = None,
        price_ts: NDArray[np.floating[Any]] | None = None,
    ) -> None:
        """Initialize pricing segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            price_st: Price for source→target flow ($/kWh per period)
            price_ts: Price for target→source flow ($/kWh per period)

        """
        super().__init__(segment_id, n_periods, periods, solver)

        # Create single power variable per direction (lossless segment, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        # Set tracked params (these trigger reactive infrastructure)
        self.price_st = price_st.astype(np.float64) if price_st is not None else None
        self.price_ts = price_ts.astype(np.float64) if price_ts is not None else None

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

    @cost
    def transfer_cost(self) -> highs_linear_expression | None:
        """Return cost expression for transfer pricing."""
        cost_terms = []

        if self.price_st is not None:
            # Cost = power * price * period duration
            cost_terms.append(Highs.qsum(self._power_st * self.price_st * self._periods))

        if self.price_ts is not None:
            cost_terms.append(Highs.qsum(self._power_ts * self.price_ts * self._periods))

        if not cost_terms:
            return None

        if len(cost_terms) == 1:
            return cost_terms[0]

        return Highs.qsum(cost_terms)


__all__ = ["PricingSegment"]
