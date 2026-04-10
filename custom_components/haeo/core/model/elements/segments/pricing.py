"""Pricing segment that adds transfer costs to the objective.

Adds cost proportional to power flow:
    cost = power * price * period_duration

When scoped to a tag, prices only that tag's power flow.
When unscoped, prices the total (sum across all tags).
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


class PricingSegmentSpec(TypedDict):
    """Specification for creating a PricingSegment."""

    segment_type: Literal["pricing"]
    tag: NotRequired[int | None]
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class PricingSegment(Segment):
    """Segment that adds transfer pricing costs.

    Uses the base class's per-tag variables (lossless: in == out per tag).

    Cost contribution:
        cost_st = sum(power_st * price_source_target * periods)
        cost_ts = sum(power_ts * price_target_source * periods)

    Prices are in $/kWh, power in kW, periods in hours.

    When scoped to a tag, power_in_st/ts return that tag's variables,
    so the cost applies only to that tag's flow.
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
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        """Initialize pricing segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
        )
        # Optional tag scope
        self._scoped_tag = spec.get("tag")

        # Set tracked params (these trigger reactive infrastructure)
        self.price_source_target = broadcast_to_sequence(spec.get("price_source_target"), self._n_periods)
        self.price_target_source = broadcast_to_sequence(spec.get("price_target_source"), self._n_periods)

    @cost
    def transfer_cost(self) -> highs_linear_expression | None:
        """Return cost expression for transfer pricing."""
        cost_terms = []

        if self.price_source_target is not None:
            # power_in_st is tag-scoped or sum depending on self._scoped_tag
            cost_terms.append(Highs.qsum(self.power_in_st * self.price_source_target * self.periods))

        if self.price_target_source is not None:
            cost_terms.append(Highs.qsum(self.power_in_ts * self.price_target_source * self.periods))

        if not cost_terms:
            return None

        if len(cost_terms) == 1:
            return cost_terms[0]

        return Highs.qsum(cost_terms)


__all__ = ["PricingSegment", "PricingSegmentSpec"]
