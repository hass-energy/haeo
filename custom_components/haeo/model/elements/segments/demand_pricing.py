"""Demand pricing segment for peak demand tariffs."""

from datetime import datetime, tzinfo
from typing import Any, Final, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression, highs_var
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import TrackedParam, constraint, cost
from custom_components.haeo.model.util import broadcast_to_sequence

from .segment import Segment

DEFAULT_DEMAND_BLOCK_HOURS: Final = 0.5
DEFAULT_DEMAND_DAYS: Final = 1.0


type DemandPricingSegmentType = Literal["demand_pricing"]


class DemandPricingSegmentSpec(TypedDict):
    """Specification for creating a DemandPricingSegment."""

    segment_type: DemandPricingSegmentType
    demand_window_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    demand_window_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]
    demand_price_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    demand_price_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]
    demand_block_hours: NotRequired[float | None]
    demand_days: NotRequired[float | None]


class DemandPricingSegment(Segment):
    """Segment that adds demand-based peak pricing.

    Demand pricing applies the maximum block-average power within demand windows.
    Block averages are computed during model setup to keep the formulation linear.
    """

    demand_window_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    demand_window_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    demand_price_source_target: TrackedParam[float | None] = TrackedParam()
    demand_price_target_source: TrackedParam[float | None] = TrackedParam()
    demand_block_hours: TrackedParam[float] = TrackedParam()
    demand_days: TrackedParam[float] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        period_start_times: NDArray[np.floating[Any]] | None = None,
        timezone: tzinfo | None = None,
        spec: DemandPricingSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        """Initialize demand pricing segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            spec: Demand pricing segment specification
            source_element: Connected source element reference
            target_element: Connected target element reference

        """
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            period_start_times=period_start_times,
            timezone=timezone,
            source_element=source_element,
            target_element=target_element,
        )

        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        self.demand_window_source_target = broadcast_to_sequence(spec.get("demand_window_source_target"), n_periods)
        self.demand_window_target_source = broadcast_to_sequence(spec.get("demand_window_target_source"), n_periods)
        self.demand_price_source_target = _as_float(spec.get("demand_price_source_target"))
        self.demand_price_target_source = _as_float(spec.get("demand_price_target_source"))
        block_hours = _as_float(spec.get("demand_block_hours"))
        self.demand_block_hours = DEFAULT_DEMAND_BLOCK_HOURS if block_hours is None else block_hours
        demand_days = _as_float(spec.get("demand_days"))
        self.demand_days = DEFAULT_DEMAND_DAYS if demand_days is None else demand_days

        self._peak_st: highs_var | None = (
            solver.addVariable(lb=0, name=f"{segment_id}_peak_st")
            if self.demand_price_source_target is not None
            else None
        )
        self._peak_ts: highs_var | None = (
            solver.addVariable(lb=0, name=f"{segment_id}_peak_ts")
            if self.demand_price_target_source is not None
            else None
        )

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

    @constraint
    def peak_source_target(self) -> list[highs_linear_expression] | None:
        """Peak demand constraints for source→target direction."""
        if self._peak_st is None or self.demand_price_source_target is None:
            return None
        return self._build_peak_constraints(
            power=self._power_st,
            window=self.demand_window_source_target,
            peak=self._peak_st,
        )

    @constraint
    def peak_target_source(self) -> list[highs_linear_expression] | None:
        """Peak demand constraints for target→source direction."""
        if self._peak_ts is None or self.demand_price_target_source is None:
            return None
        return self._build_peak_constraints(
            power=self._power_ts,
            window=self.demand_window_target_source,
            peak=self._peak_ts,
        )

    @cost
    def demand_cost(self) -> highs_linear_expression | None:
        """Return cost expression for demand pricing."""
        cost_terms: list[highs_linear_expression] = []

        if self._peak_st is not None and self.demand_price_source_target is not None:
            cost_terms.append(self._peak_st * self.demand_price_source_target * self.demand_days)
        if self._peak_ts is not None and self.demand_price_target_source is not None:
            cost_terms.append(self._peak_ts * self.demand_price_target_source * self.demand_days)

        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)

    def _build_peak_constraints(
        self,
        *,
        power: HighspyArray,
        window: NDArray[np.float64] | None,
        peak: highs_var,
    ) -> list[highs_linear_expression] | None:
        block_hours = self.demand_block_hours
        if block_hours <= 0:
            msg = "demand_block_hours must be positive"
            raise ValueError(msg)

        weights = self._block_weights(block_hours)
        if not weights:
            return None

        window_values = np.ones(self._n_periods, dtype=np.float64) if window is None else window

        constraints: list[highs_linear_expression] = []
        for weight in weights:
            if window is not None:
                mask = weight > 0
                if not np.any(mask):
                    continue
                block_windows = window_values[mask]
                if float(block_windows.max() - block_windows.min()) > 1e-9:
                    continue
                window_weight = float(block_windows[0])
                if window_weight <= 0:
                    continue
            else:
                window_weight = 1.0
            block_average = Highs.qsum(power * weight)
            constraints.append(peak >= block_average * window_weight)

        return constraints or None

    def _block_weights(self, block_hours: float) -> list[NDArray[np.float64]]:
        boundaries = np.concatenate(([0.0], np.cumsum(self._periods, dtype=np.float64)))
        total_hours = float(boundaries[-1])
        if total_hours <= 0:
            return []

        weights: list[NDArray[np.float64]] = []
        offset = self._block_anchor_offset(block_hours)
        block_start = -offset
        while block_start < total_hours - 1e-9:
            block_end = block_start + block_hours
            if block_start < 0 or block_end > total_hours + 1e-9:
                block_start = block_end
                continue
            duration = block_end - block_start
            if duration <= 0:
                break

            overlaps = np.minimum(boundaries[1:], block_end) - np.maximum(boundaries[:-1], block_start)
            overlaps = np.clip(overlaps, 0.0, None)
            weights.append((overlaps / duration).astype(np.float64))
            block_start = block_end

        return weights

    def _block_anchor_offset(self, block_hours: float) -> float:
        if block_hours <= 0:
            return 0.0
        if self._period_start_times is None or self._period_start_times.size == 0:
            return 0.0
        start_time = float(self._period_start_times[0])
        if self._period_start_timezone is None:
            start_dt = datetime.fromtimestamp(start_time)
        else:
            start_dt = datetime.fromtimestamp(start_time, tz=self._period_start_timezone)
        hours_since_midnight = (
            start_dt.hour
            + start_dt.minute / 60.0
            + start_dt.second / 3600.0
            + start_dt.microsecond / 3_600_000_000.0
        )
        return hours_since_midnight % block_hours


def _as_float(value: NDArray[np.floating[Any]] | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        return float(value.flat[0])
    return float(value)


__all__ = [
    "DEFAULT_DEMAND_BLOCK_HOURS",
    "DEFAULT_DEMAND_DAYS",
    "DemandPricingSegment",
    "DemandPricingSegmentSpec",
    "DemandPricingSegmentType",
]
