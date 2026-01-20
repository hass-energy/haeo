"""Connection segment types for composable connection architecture.

Each segment type applies a specific transformation or constraint to power flow:
- DemandPricingSegment: Adds peak demand pricing costs
- EfficiencySegment: Applies efficiency losses
- PassthroughSegment: Lossless passthrough (no constraints)
- PowerLimitSegment: Limits power flow with optional time-slice constraint
- PricingSegment: Adds transfer pricing costs
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Literal, TypeGuard

from highspy import Highs
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.element import Element

from .battery_balance import (
    BALANCE_ABSORBED_EXCESS,
    BALANCE_POWER_DOWN,
    BALANCE_POWER_UP,
    BALANCE_UNMET_DEMAND,
    BatteryBalanceOutputName,
    BatteryBalanceSegment,
    BatteryBalanceSegmentSpec,
)
from .demand_pricing import DemandPricingSegment, DemandPricingSegmentSpec
from .efficiency import EfficiencySegment, EfficiencySegmentSpec
from .passthrough import PassthroughSegment, PassthroughSegmentSpec
from .power_limit import (
    POWER_LIMIT_SOURCE_TARGET,
    POWER_LIMIT_TARGET_SOURCE,
    POWER_LIMIT_TIME_SLICE,
    PowerLimitOutputName,
    PowerLimitSegment,
    PowerLimitSegmentSpec,
)
from .pricing import PricingSegment, PricingSegmentSpec
from .segment import Segment

# Discriminated union of segment type strings
type SegmentType = Literal[
    "battery_balance",
    "demand_pricing",
    "efficiency",
    "passthrough",
    "power_limit",
    "pricing",
]

# Union type for all segment specifications
type SegmentSpec = (
    BatteryBalanceSegmentSpec
    | DemandPricingSegmentSpec
    | EfficiencySegmentSpec
    | PassthroughSegmentSpec
    | PowerLimitSegmentSpec
    | PricingSegmentSpec
)


def is_efficiency_spec(spec: SegmentSpec) -> TypeGuard[EfficiencySegmentSpec]:
    """Return True when spec is for an efficiency segment."""
    return spec["segment_type"] == "efficiency"


def is_passthrough_spec(spec: SegmentSpec) -> TypeGuard[PassthroughSegmentSpec]:
    """Return True when spec is for a passthrough segment."""
    return spec["segment_type"] == "passthrough"


def is_power_limit_spec(spec: SegmentSpec) -> TypeGuard[PowerLimitSegmentSpec]:
    """Return True when spec is for a power limit segment."""
    return spec["segment_type"] == "power_limit"


def is_pricing_spec(spec: SegmentSpec) -> TypeGuard[PricingSegmentSpec]:
    """Return True when spec is for a pricing segment."""
    return spec["segment_type"] == "pricing"


def is_demand_pricing_spec(spec: SegmentSpec) -> TypeGuard[DemandPricingSegmentSpec]:
    """Return True when spec is for a demand pricing segment."""
    return spec["segment_type"] == "demand_pricing"


@dataclass(frozen=True, slots=True)
class SegmentSpecEntry:
    """Specification for a segment type."""

    factory: Callable[..., Segment]


# Registry mapping segment type strings to segment factories
SEGMENTS: Final[dict[SegmentType, SegmentSpecEntry]] = {
    "battery_balance": SegmentSpecEntry(factory=BatteryBalanceSegment),
    "demand_pricing": SegmentSpecEntry(factory=DemandPricingSegment),
    "efficiency": SegmentSpecEntry(factory=EfficiencySegment),
    "passthrough": SegmentSpecEntry(factory=PassthroughSegment),
    "power_limit": SegmentSpecEntry(factory=PowerLimitSegment),
    "pricing": SegmentSpecEntry(factory=PricingSegment),
}


def create_segment(
    *,
    segment_id: str,
    n_periods: int,
    periods: NDArray[np.floating[Any]],
    solver: Highs,
    spec: SegmentSpec,
    source_element: Element[Any],
    target_element: Element[Any],
) -> Segment:
    """Create a segment instance from a segment specification."""
    segment_type = spec["segment_type"]
    entry = SEGMENTS[segment_type]
    return entry.factory(
        segment_id,
        n_periods,
        periods,
        solver,
        spec=spec,
        source_element=source_element,
        target_element=target_element,
    )

__all__ = [
    "BALANCE_ABSORBED_EXCESS",
    "BALANCE_POWER_DOWN",
    "BALANCE_POWER_UP",
    "BALANCE_UNMET_DEMAND",
    "POWER_LIMIT_SOURCE_TARGET",
    "POWER_LIMIT_TARGET_SOURCE",
    "POWER_LIMIT_TIME_SLICE",
    "SEGMENTS",
    "BatteryBalanceOutputName",
    "BatteryBalanceSegment",
    "BatteryBalanceSegmentSpec",
    "DemandPricingSegment",
    "DemandPricingSegmentSpec",
    "EfficiencySegment",
    "EfficiencySegmentSpec",
    "PassthroughSegment",
    "PassthroughSegmentSpec",
    "PowerLimitOutputName",
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
    "PricingSegment",
    "PricingSegmentSpec",
    "Segment",
    "SegmentSpec",
    "SegmentSpecEntry",
    "SegmentType",
    "create_segment",
    "is_demand_pricing_spec",
    "is_efficiency_spec",
    "is_passthrough_spec",
    "is_power_limit_spec",
    "is_pricing_spec",
]
