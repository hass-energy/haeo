"""Connection segment types for composable connection architecture.

Each segment type applies a specific transformation or constraint to power flow:
- EfficiencySegment: Applies efficiency losses
- PassthroughSegment: Lossless passthrough (no constraints)
- PowerLimitSegment: Limits power flow with optional time-slice constraint
- PricingSegment: Adds transfer pricing costs
"""

from typing import Final, Literal, TypeGuard

from .efficiency import EFFICIENCY_PERCENT, EfficiencySegment, EfficiencySegmentSpec
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
type SegmentType = Literal["efficiency", "passthrough", "power_limit", "pricing"]

# Union type for all segment specifications
type SegmentSpec = EfficiencySegmentSpec | PassthroughSegmentSpec | PowerLimitSegmentSpec | PricingSegmentSpec


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


# Registry mapping segment type strings to segment classes
SEGMENT_TYPES: Final[dict[SegmentType, type[Segment]]] = {
    "efficiency": EfficiencySegment,
    "passthrough": PassthroughSegment,
    "power_limit": PowerLimitSegment,
    "pricing": PricingSegment,
}

__all__ = [
    "EFFICIENCY_PERCENT",
    "POWER_LIMIT_SOURCE_TARGET",
    "POWER_LIMIT_TARGET_SOURCE",
    "POWER_LIMIT_TIME_SLICE",
    "SEGMENT_TYPES",
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
    "SegmentType",
    "is_efficiency_spec",
    "is_passthrough_spec",
    "is_power_limit_spec",
    "is_pricing_spec",
]
