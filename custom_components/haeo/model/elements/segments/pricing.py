"""Pricing segment that adds transfer costs to the objective.

Adds cost proportional to power flow:
    cost = power * price * period_duration
"""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.model.reactive import TrackedParam, cost

from .segment import Segment


class PricingSegmentSpec(TypedDict):
    """Specification for creating a PricingSegment."""

    segment_type: Literal["pricing"]
    name: NotRequired[str]
    price_source_target: NotRequired[NDArray[np.floating[Any]]]
    price_target_source: NotRequired[NDArray[np.floating[Any]]]


class PricingSegment(Segment):
    """Segment that adds transfer pricing costs.

    Creates single power variables for each direction (lossless, in == out).

    Cost contribution:
        cost_st = sum(power_st * price_source_target * periods)
        cost_ts = sum(power_ts * price_target_source * periods)

    Prices are in $/kWh, power in kW, periods in hours.

    Uses TrackedParam for prices to enable warm-start optimization.
    """

    # TrackedParams for warm-start support
    price_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    price_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: PricingSegmentSpec,
    ) -> None:
        """Initialize pricing segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            spec: Pricing segment specification.

        """
        super().__init__(segment_id, n_periods, periods, solver)
        # Create single power variable per direction (lossless segment, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        # Set tracked params (these trigger reactive infrastructure)
        price_source_target = spec.get("price_source_target")
        if price_source_target is not None:
            self.price_source_target = np.asarray(price_source_target, dtype=np.float64)
        else:
            self.price_source_target = None

        price_target_source = spec.get("price_target_source")
        if price_target_source is not None:
            self.price_target_source = np.asarray(price_target_source, dtype=np.float64)
        else:
            self.price_target_source = None

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

        if self.price_source_target is not None:
            # Cost = power * price * period duration
            cost_terms.append(Highs.qsum(self._power_st * self.price_source_target * self._periods))

        if self.price_target_source is not None:
            cost_terms.append(Highs.qsum(self._power_ts * self.price_target_source * self._periods))

        if not cost_terms:
            return None

        if len(cost_terms) == 1:
            return cost_terms[0]

        return Highs.qsum(cost_terms)


__all__ = ["PricingSegment", "PricingSegmentSpec"]
