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
    tag_costs: NotRequired[list[dict[str, Any]]]


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
        power_in: HighspyArray,
        tag_flows_in: dict[int, HighspyArray] | None = None,
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
            tag_flows_in=tag_flows_in,
        )
        self.price = broadcast_to_sequence(spec.get("price"), self._n_periods)
        self._tag_costs: list[dict[str, Any]] = spec.get("tag_costs") or []

    @cost
    def transfer_cost(self) -> highs_linear_expression | None:
        """Cost proportional to power flow."""
        if self.price is None:
            return None
        return Highs.qsum(self._power_in * self.price * self.periods)

    @cost
    def tag_transfer_cost(self) -> highs_linear_expression | None:
        """Per-tag surcharge cost."""
        if not self._tag_costs or not self._tag_flows_in:
            return None
        costs: list[highs_linear_expression] = []
        for tc in self._tag_costs:
            tag = tc["tag"]
            price = broadcast_to_sequence(tc.get("price"), self._n_periods)
            if price is not None and tag in self._tag_flows_in:
                tag_flow = self._tag_flows_in[tag]
                costs.append(Highs.qsum(tag_flow * price * self.periods))
        if not costs:
            return None
        return Highs.qsum(costs) if len(costs) > 1 else costs[0]


__all__ = ["PricingSegment", "PricingSegmentSpec"]
