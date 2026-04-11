"""Power limit segment — identity transform with constraint side-effects."""

from typing import Any, Final, Literal, NotRequired

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, constraint
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment, TagPowerMap, _sum_tag_map

type PowerLimitOutputName = Literal["source_target", "target_source", "time_slice"]

POWER_LIMIT_SOURCE_TARGET: Final = "source_target"
POWER_LIMIT_TARGET_SOURCE: Final = "target_source"
POWER_LIMIT_TIME_SLICE: Final = "time_slice"


class PowerLimitSegmentSpec(TypedDict):
    """Specification for creating a PowerLimitSegment."""

    segment_type: Literal["power_limit"]
    max_power_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    max_power_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]
    fixed: NotRequired[bool | None]


class PowerLimitSegment(Segment):
    """Identity transform that constrains maximum power flow."""

    max_power_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    max_power_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: PowerLimitSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        super().__init__(
            segment_id, n_periods, periods, solver, source_element=source_element, target_element=target_element
        )
        self._fixed = spec.get("fixed", False)
        self.max_power_source_target = broadcast_to_sequence(spec.get("max_power_source_target"), self._n_periods)
        self.max_power_target_source = broadcast_to_sequence(spec.get("max_power_target_source"), self._n_periods)

    def apply(self, power_st: TagPowerMap, power_ts: TagPowerMap) -> tuple[TagPowerMap, TagPowerMap]:
        self._power_in_st = self._power_out_st = power_st
        self._power_in_ts = self._power_out_ts = power_ts
        return power_st, power_ts

    @constraint(output=True, unit="$/kW")
    def source_target(self) -> list[highs_linear_expression] | None:
        if self.max_power_source_target is None or not self._power_in_st:
            return None
        total = _sum_tag_map(self._power_in_st)
        if self._fixed:
            return list(total == self.max_power_source_target)
        return list(total <= self.max_power_source_target)

    @constraint(output=True, unit="$/kW")
    def target_source(self) -> list[highs_linear_expression] | None:
        if self.max_power_target_source is None or not self._power_in_ts:
            return None
        total = _sum_tag_map(self._power_in_ts)
        if self._fixed:
            return list(total == self.max_power_target_source)
        return list(total <= self.max_power_target_source)

    @constraint(output=True, unit="$/kW")
    def time_slice(self) -> list[highs_linear_expression] | None:
        if self.max_power_source_target is None or self.max_power_target_source is None:
            return None
        if not self._power_in_st or not self._power_in_ts:
            return None
        total_st = _sum_tag_map(self._power_in_st)
        total_ts = _sum_tag_map(self._power_in_ts)
        coeff_st = np.divide(
            1.0, self.max_power_source_target, out=np.zeros(self._n_periods), where=self.max_power_source_target > 0
        )
        coeff_ts = np.divide(
            1.0, self.max_power_target_source, out=np.zeros(self._n_periods), where=self.max_power_target_source > 0
        )
        return list(total_st * coeff_st + total_ts * coeff_ts <= 1.0)


__all__ = [
    "POWER_LIMIT_SOURCE_TARGET",
    "POWER_LIMIT_TARGET_SOURCE",
    "POWER_LIMIT_TIME_SLICE",
    "PowerLimitOutputName",
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
]
