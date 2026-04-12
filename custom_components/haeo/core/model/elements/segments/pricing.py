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
    """Specification for creating a PricingSegment."""

    segment_type: Literal["pricing"]
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


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
        direction: str,
    ) -> None:
        """Initialize pricing segment.

        Args:
            spec: Segment specification with directional prices.
            direction: "st" or "ts" — determines which price to use.

        """
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            power_in=power_in,
        )
        if direction == "st":
            self.price = broadcast_to_sequence(spec.get("price_source_target"), self._n_periods)
        else:
            self.price = broadcast_to_sequence(spec.get("price_target_source"), self._n_periods)

    @cost
    def transfer_cost(self) -> highs_linear_expression | None:
        """Cost proportional to power flow."""
        if self.price is None:
            return None
        return Highs.qsum(self._power_in * self.price * self.periods)


__all__ = ["PricingSegment", "PricingSegmentSpec"]
