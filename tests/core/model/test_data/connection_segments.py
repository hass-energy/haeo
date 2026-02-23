"""Scenario data for connection tests that focus on segments."""

from collections.abc import Sequence

import numpy as np

from .segment_types import ConnectionScenario


CONNECTION_SCENARIOS: Sequence[ConnectionScenario] = [
    {
        "description": "Connection uses dict keys for segment names",
        "periods": np.array([1.0]),
        "segments": {"efficiency": {"segment_type": "efficiency", "efficiency_source_target": np.array([0.90])}},
        "inputs": {},
        "expected_outputs": {"segment_names": ["efficiency"], "segment_types": ["EfficiencySegment"]},
    },
    {
        "description": "Connection defaults to passthrough segment",
        "periods": np.array([1.0, 1.0]),
        "segments": None,
        "inputs": {},
        "expected_outputs": {"segment_names": ["passthrough"], "segment_types": ["PassthroughSegment"]},
    },
    {
        "description": "Connection caps source-to-target flow",
        "periods": np.array([1.0, 1.0]),
        "segments": {"power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0])}},
        "inputs": {"maximize": {"power_source_target": 1.0}},
        "expected_outputs": {"power_source_target": [5.0, 5.0]},
    },
    {
        "description": "Connection caps target-to-source flow",
        "periods": np.array([1.0, 1.0]),
        "segments": {"power_limit": {"segment_type": "power_limit", "max_power_target_source": np.array([3.0, 3.0])}},
        "inputs": {"maximize": {"power_target_source": 1.0}},
        "expected_outputs": {"power_target_source": [3.0, 3.0]},
    },
    {
        "description": "Connection efficiency reduces power into target",
        "periods": np.array([1.0]),
        "segments": {"efficiency": {"segment_type": "efficiency", "efficiency_source_target": np.array([0.90])}},
        "inputs": {"power_source_target": [10.0], "power_target_source": [0.0]},
        "expected_outputs": {"power_into_target": [9.0]},
    },
    {
        "description": "Connection pricing adds cost to objective",
        "periods": np.array([1.0]),
        "segments": {"pricing": {"segment_type": "pricing", "price_source_target": np.array([0.1])}},
        "inputs": {"power_source_target": [10.0], "power_target_source": [0.0], "minimize_cost": True},
        "expected_outputs": {"objective_value": 1.0},
    },
    {
        "description": "Connection segments support name and index access",
        "periods": np.array([1.0, 1.0]),
        "segments": {
            "power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0])},
            "pricing": {"segment_type": "pricing", "price_source_target": np.array([0.1, 0.1])},
        },
        "inputs": {
            "updates": [
                ("power_limit", "max_power_source_target", [10.0, 10.0]),
                ("pricing", "price_source_target", [0.2, 0.2]),
            ]
        },
        "expected_outputs": {
            "segment_names": ["power_limit", "pricing"],
            "segment_types": ["PowerLimitSegment", "PricingSegment"],
            "segment_types_by_index": ["PowerLimitSegment", "PricingSegment"],
            "power_limit_max_power_source_target": [10.0, 10.0],
            "pricing_price_source_target": [0.2, 0.2],
        },
    },
]
