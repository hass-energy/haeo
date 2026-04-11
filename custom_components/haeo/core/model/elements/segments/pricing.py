"""Pricing segment that adds transfer costs to the objective.

Identity transform with cost side-effect:
    cost = power * price * period_duration
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
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class PricingSegment(Segment):
    """Segment that adds transfer pricing costs.

    Identity transform — returns input power unchanged.
    Adds cost = power * price * period to the objective.
    """

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
        self.price_source_target = broadcast_to_sequence(spec.get("price_source_target"), self._n_periods)
        self.price_target_source = broadcast_to_sequence(spec.get("price_target_source"), self._n_periods)

    def apply(self, power_st: HighspyArray, power_ts: HighspyArray) -> tuple[HighspyArray, HighspyArray]:
        """Identity: return input unchanged. Cost computed from stored references."""
        self._power_in_st = self._power_out_st = power_st
        self._power_in_ts = self._power_out_ts = power_ts
        return power_st, power_ts

    @cost
    def transfer_cost(self) -> highs_linear_expression | None:
        """Return cost expression for transfer pricing."""
        cost_terms = []

        if self.price_source_target is not None and self._power_in_st is not None:
            cost_terms.append(Highs.qsum(self._power_in_st * self.price_source_target * self.periods))

        if self.price_target_source is not None and self._power_in_ts is not None:
            cost_terms.append(Highs.qsum(self._power_in_ts * self.price_target_source * self.periods))

        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)


__all__ = ["PricingSegment", "PricingSegmentSpec"]
