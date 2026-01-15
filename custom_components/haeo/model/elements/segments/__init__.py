"""Connection segment types for composable connection architecture.

Each segment type applies a specific transformation or constraint to power flow:
- EfficiencySegment: Applies efficiency losses
- PassthroughSegment: Lossless passthrough (no constraints)
- PowerLimitSegment: Limits power flow with optional time-slice constraint
- PricingSegment: Adds transfer pricing costs
"""

from typing import Final, Literal

from .efficiency import EFFICIENCY_PERCENT, EfficiencySegment, EfficiencySegmentSpec
from .passthrough import PassthroughSegment, PassthroughSegmentSpec
from .power_limit import PowerLimitSegment, PowerLimitSegmentSpec
from .pricing import PricingSegment, PricingSegmentSpec
from .segment import Segment

# Discriminated union of segment type strings
type SegmentType = Literal["efficiency", "passthrough", "power_limit", "pricing"]

# Union type for all segment specifications
type SegmentSpec = EfficiencySegmentSpec | PassthroughSegmentSpec | PowerLimitSegmentSpec | PricingSegmentSpec

# Registry mapping segment type strings to segment classes
SEGMENT_TYPES: Final[dict[SegmentType, type[Segment]]] = {
    "efficiency": EfficiencySegment,
    "passthrough": PassthroughSegment,
    "power_limit": PowerLimitSegment,
    "pricing": PricingSegment,
}

__all__ = [
    "EFFICIENCY_PERCENT",
    "SEGMENT_TYPES",
    "EfficiencySegment",
    "EfficiencySegmentSpec",
    "PassthroughSegment",
    "PassthroughSegmentSpec",
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
    "PricingSegment",
    "PricingSegmentSpec",
    "Segment",
    "SegmentType",
    "SegmentSpec",
]
