"""Connection segment types for composable connection architecture.

Each segment type applies a specific transformation or constraint to power flow:
- EfficiencySegment: Applies efficiency losses
- PassthroughSegment: Lossless passthrough (no constraints)
- PowerLimitSegment: Limits power flow with optional time-slice constraint
- PricingSegment: Adds transfer pricing costs
"""

from typing import Final

from .efficiency import EFFICIENCY_PERCENT, EfficiencySegment
from .passthrough import PassthroughSegment
from .power_limit import PowerLimitSegment
from .pricing import PricingSegment
from .segment import Segment

# Registry mapping segment type strings to segment classes
SEGMENT_TYPES: Final[dict[str, type[Segment]]] = {
    "efficiency": EfficiencySegment,
    "passthrough": PassthroughSegment,
    "power_limit": PowerLimitSegment,
    "pricing": PricingSegment,
}

__all__ = [
    "EFFICIENCY_PERCENT",
    "EfficiencySegment",
    "PassthroughSegment",
    "PowerLimitSegment",
    "PricingSegment",
    "SEGMENT_TYPES",
    "Segment",
]
