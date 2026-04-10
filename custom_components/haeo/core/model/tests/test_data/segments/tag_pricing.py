"""Tag pricing segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.core.model.elements.segments import TagPricingSegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Tag pricing adds cost to objective",
        "factory": TagPricingSegment,
        "spec": {
            "segment_type": "tag_pricing",
            "tag": "solar",
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
    {
        "description": "Tag pricing with only source-to-target price",
        "factory": TagPricingSegment,
        "spec": {
            "segment_type": "tag_pricing",
            "tag": "grid_import",
            "price_source_target": np.array([0.30, 0.30]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {
            "power_in_st": [5.0, 5.0],
            "power_in_ts": [0.0, 0.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 3.0},
    },
    {
        "description": "Tag pricing with no prices returns zero cost",
        "factory": TagPricingSegment,
        "spec": {
            "segment_type": "tag_pricing",
            "tag": "battery",
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {
            "power_in_st": [10.0, 10.0],
            "power_in_ts": [5.0, 5.0],
            "maximize": {"power_in_st": 1.0},
        },
        "expected_outputs": {
            "power_in_st": (10.0, 10.0),
            "power_in_ts": (5.0, 5.0),
        },
    },
]
