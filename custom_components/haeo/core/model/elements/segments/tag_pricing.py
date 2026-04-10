"""Tag pricing segment that adds transfer costs for tagged power flows.

Adds cost proportional to power flow for a specific tag:
    cost = power * price * period_duration

This is similar to PricingSegment but is intended to price a specific
category of power flow (e.g., "grid_import", "solar") rather than all flow.
"""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, cost
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment


class TagPricingSegmentSpec(TypedDict):
    """Specification for creating a TagPricingSegment."""

    segment_type: Literal["tag_pricing"]
    tag: str
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class TagPricingSegment(Segment):
    """Segment that adds transfer pricing costs for a specific power flow tag.

    Creates single power variables for each direction (lossless, in == out).

    Cost contribution:
        cost_st = sum(power_st * price_source_target * periods)
        cost_ts = sum(power_ts * price_target_source * periods)

    Prices are in $/kWh, power in kW, periods in hours.

    The tag field identifies which category of power flow this pricing applies to.
    This enables tariff-based pricing where different power sources or destinations
    are charged at different rates.

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
        spec: TagPricingSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        """Initialize tag pricing segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            spec: Tag pricing segment specification.
            source_element: Connected source element reference
            target_element: Connected target element reference

        """
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
        )
        self._tag = spec["tag"]

        # Create single power variable per direction (lossless segment, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        # Set tracked params (these trigger reactive infrastructure)
        self.price_source_target = broadcast_to_sequence(spec.get("price_source_target"), self._n_periods)
        self.price_target_source = broadcast_to_sequence(spec.get("price_target_source"), self._n_periods)

    @property
    def tag(self) -> str:
        """Return the tag name for this pricing segment."""
        return self._tag

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
        """Return cost expression for tagged transfer pricing."""
        cost_terms = []

        if self.price_source_target is not None:
            cost_terms.append(Highs.qsum(self._power_st * self.price_source_target * self.periods))

        if self.price_target_source is not None:
            cost_terms.append(Highs.qsum(self._power_ts * self.price_target_source * self.periods))

        if not cost_terms:
            return None

        if len(cost_terms) == 1:
            return cost_terms[0]

        return Highs.qsum(cost_terms)


__all__ = ["TagPricingSegment", "TagPricingSegmentSpec"]
