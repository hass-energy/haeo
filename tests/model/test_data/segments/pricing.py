"""Pricing segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.model.elements.segments import PricingSegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Pricing adds cost to objective",
        "factory": PricingSegment,
        "spec": {
            "segment_type": "pricing",
            "price_source_target": np.array([0.1, 0.1]),
            "price_target_source": np.array([0.2, 0.2]),
        },
        "periods": np.array([1.0, 0.5]),
        "inputs": {
            "power_in_st": [10.0, 10.0],
            "power_in_ts": [5.0, 5.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 3.0},
    },
]
