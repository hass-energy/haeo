"""Pricing segment — adds transfer cost proportional to power flow."""

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
    """Specification for creating a PricingSegment.

    Directional fields (price_source_target, price_target_source) are resolved
    by the Connection into a single `price` value before construction.
    """

    segment_type: Literal["pricing"]
    price: NotRequired[NDArray[np.floating[Any]] | float | None]
    # Directional aliases — resolved by Connection, not used by segment directly
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]
    tag_prices: NotRequired[list[dict[str, Any]]]


class PricingSegment(Segment):
    """Adds transfer pricing cost proportional to power flow."""

    price: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

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
        power_in: dict[int, HighspyArray],
    ) -> None:
        """Initialize pricing segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            power_in=power_in,
        )
        self.price = broadcast_to_sequence(spec.get("price"), self._n_periods)
        self._tag_prices: dict[int, NDArray[np.float64]] = {
            tp["tag"]: price
            for tp in (spec.get("tag_prices") or [])
            if (price := broadcast_to_sequence(tp.get("price"), self._n_periods)) is not None
        }

    @cost
    def transfer_cost(self) -> highs_linear_expression | None:
        """Cost proportional to power flow."""
        if self.price is None:
            return None
        return Highs.qsum(self.total_power_in * self.price * self.periods)

    @cost
    def tag_transfer_cost(self) -> highs_linear_expression | None:
        """Per-tag surcharge cost."""
        if not self._tag_prices:
            return None
        costs = [
            Highs.qsum(self._power_in[tag] * price * self.periods)
            for tag, price in self._tag_prices.items()
            if tag in self._power_in
        ]
        if not costs:
            return None
        return Highs.qsum(costs) if len(costs) > 1 else costs[0]


__all__ = ["PricingSegment", "PricingSegmentSpec"]
