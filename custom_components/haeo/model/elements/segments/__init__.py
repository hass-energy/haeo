"""Connection segment types for composable connection architecture.

Each segment type applies a specific transformation or constraint to power flow:
- EfficiencySegment: Applies efficiency losses
- PassthroughSegment: Lossless passthrough (no constraints)
- PowerLimitSegment: Limits power flow with optional time-slice constraint
- PricingSegment: Adds transfer pricing costs
"""

from .efficiency import EfficiencySegment
from .passthrough import PassthroughSegment
from .power_limit import PowerLimitSegment
from .pricing import PricingSegment
from .segment import Segment

__all__ = [
    "EfficiencySegment",
    "PassthroughSegment",
    "PowerLimitSegment",
    "PricingSegment",
    "Segment",
]
