"""Demand pricing segment scenarios."""

import numpy as np

from custom_components.haeo.model.elements.segments import DemandPricingSegment

from ..segment_types import SegmentScenario

SCENARIOS: list[SegmentScenario] = [
    {
        "description": "Demand pricing adds peak cost",
        "factory": DemandPricingSegment,
        "spec": {
            "segment_type": "demand_pricing",
            "demand_price_source_target": 10.0,
            "demand_window_source_target": np.array([1.0]),
            "demand_block_hours": 1.0,
            "demand_days": 30.0,
        },
        "periods": np.array([1.0]),
        "inputs": {
            "power_in_st": [5.0],
            "power_in_ts": [0.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 1500.0},
    }
]

__all__ = ["SCENARIOS"]
