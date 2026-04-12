"""Pricing segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.core.model.elements.segments import PricingSegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Pricing adds cost to objective",
        "factory": PricingSegment,
        "spec": {
            "segment_type": "pricing",
            "price": np.array([0.1, 0.1]),
        },
        "periods": np.array([1.0, 0.5]),
        "inputs": {
            "power_in_st": [10.0, 10.0],
            "minimize_cost": True,
        },
        # cost = 10 * 0.1 * 1.0 + 10 * 0.1 * 0.5 = 1.0 + 0.5 = 1.5
        "expected_outputs": {"objective_value": 1.5},
    },
]
