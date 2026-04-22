"""Segment scenario aggregates."""

from custom_components.haeo.core.model.tests.test_data.segment_types import SegmentErrorScenario

from .efficiency import SCENARIOS as EFFICIENCY_SCENARIOS
from .passthrough import SCENARIOS as PASSTHROUGH_SCENARIOS
from .power_limit import SCENARIOS as POWER_LIMIT_SCENARIOS
from .pricing import SCENARIOS as PRICING_SCENARIOS

SEGMENT_SCENARIOS = [
    *PASSTHROUGH_SCENARIOS,
    *EFFICIENCY_SCENARIOS,
    *POWER_LIMIT_SCENARIOS,
    *PRICING_SCENARIOS,
]

SEGMENT_ERROR_SCENARIOS: list[SegmentErrorScenario] = []

__all__ = [
    "EFFICIENCY_SCENARIOS",
    "PASSTHROUGH_SCENARIOS",
    "POWER_LIMIT_SCENARIOS",
    "PRICING_SCENARIOS",
    "SEGMENT_ERROR_SCENARIOS",
    "SEGMENT_SCENARIOS",
]
