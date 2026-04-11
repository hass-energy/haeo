"""Pricing segment — identity transform with cost side-effect."""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, cost
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment, TagPowerMap, _sum_tag_map


class PricingSegmentSpec(TypedDict):
    """Specification for creating a PricingSegment."""

    segment_type: Literal["pricing"]
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class PricingSegment(Segment):
    """Identity transform that adds transfer pricing costs."""

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
        super().__init__(
            segment_id, n_periods, periods, solver, source_element=source_element, target_element=target_element
        )
        self.price_source_target = broadcast_to_sequence(spec.get("price_source_target"), self._n_periods)
        self.price_target_source = broadcast_to_sequence(spec.get("price_target_source"), self._n_periods)

    def apply(self, power_st: TagPowerMap, power_ts: TagPowerMap) -> tuple[TagPowerMap, TagPowerMap]:
        self._power_in_st = self._power_out_st = power_st
        self._power_in_ts = self._power_out_ts = power_ts
        return power_st, power_ts

    @cost
    def transfer_cost(self) -> highs_linear_expression | None:
        cost_terms = []
        if self.price_source_target is not None and self._power_in_st:
            total_st = _sum_tag_map(self._power_in_st)
            cost_terms.append(Highs.qsum(total_st * self.price_source_target * self.periods))
        if self.price_target_source is not None and self._power_in_ts:
            total_ts = _sum_tag_map(self._power_in_ts)
            cost_terms.append(Highs.qsum(total_ts * self.price_target_source * self.periods))
        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)


__all__ = ["PricingSegment", "PricingSegmentSpec"]
