"""Tag pricing segment that adds transfer costs for tagged power flows.

Adds cost proportional to tagged power flow:
    cost = tagged_power[tag] * price * period_duration

This segment prices a specific tag of power flow within a connection's
native tagged power decomposition. The segment still has its own total
power variables (lossless passthrough), but the cost is computed from
the per-tag variables inherited from the base Segment class.
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
    When tagged power is active, the cost is computed from the per-tag variables.

    Cost contribution (when tags active):
        cost_st = sum(tagged_power_st[tag] * price_source_target * periods)
        cost_ts = sum(tagged_power_ts[tag] * price_target_source * periods)

    Cost contribution (when no tags):
        cost_st = sum(power_st * price_source_target * periods)
        cost_ts = sum(power_ts * price_target_source * periods)

    Prices are in $/kWh, power in kW, periods in hours.
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
        """Initialize tag pricing segment."""
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

        # Set tracked params
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
        """Return cost expression for tagged transfer pricing.

        When tagged power is active, prices the specific tag's power flow.
        When no tags are configured, prices the total power flow.
        """
        cost_terms = []

        if self.price_source_target is not None:
            if self.has_tags and self._tag in self._tagged_power:
                power_st = self.tagged_power_in_st(self._tag)
            else:
                power_st = self._power_st
            cost_terms.append(Highs.qsum(power_st * self.price_source_target * self.periods))

        if self.price_target_source is not None:
            if self.has_tags and self._tag in self._tagged_power:
                power_ts = self.tagged_power_in_ts(self._tag)
            else:
                power_ts = self._power_ts
            cost_terms.append(Highs.qsum(power_ts * self.price_target_source * self.periods))

        if not cost_terms:
            return None

        if len(cost_terms) == 1:
            return cost_terms[0]

        return Highs.qsum(cost_terms)


__all__ = ["TagPricingSegment", "TagPricingSegmentSpec"]
