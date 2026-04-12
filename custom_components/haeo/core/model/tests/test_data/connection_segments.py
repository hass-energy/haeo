"""Scenario data for connection tests that focus on segments."""

from collections.abc import Sequence

import numpy as np

from .segment_types import ConnectionScenario


CONNECTION_SCENARIOS: Sequence[ConnectionScenario] = [
    {
        "description": "Connection uses dict keys for segment names",
        "periods": np.array([1.0]),
        "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": np.array([0.90])}},
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
        "description": "Connection caps flow with power limit",
        "periods": np.array([1.0, 1.0]),
        "segments": {"power_limit": {"segment_type": "power_limit", "max_power": np.array([5.0, 5.0])}},
        "inputs": {"maximize": {"power_in": 1.0}},
        "expected_outputs": {"power_in": [5.0, 5.0]},
    },
    {
        "description": "Connection efficiency reduces power out",
        "periods": np.array([1.0]),
        "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": np.array([0.90])}},
        "inputs": {"power_in": [10.0]},
        "expected_outputs": {"power_out": [9.0]},
    },
    {
        "description": "Connection pricing adds cost to objective",
        "periods": np.array([1.0]),
        "segments": {"pricing": {"segment_type": "pricing", "price": np.array([0.1])}},
        "inputs": {"power_in": [10.0], "minimize_cost": True},
        "expected_outputs": {"objective_value": 1.0},
    },
    {
        "description": "Connection segments support name and index access",
        "periods": np.array([1.0, 1.0]),
        "segments": {
            "power_limit": {"segment_type": "power_limit", "max_power": np.array([5.0, 5.0])},
            "pricing": {"segment_type": "pricing", "price": np.array([0.1, 0.1])},
        },
        "inputs": {
            "updates": [
                ("power_limit", "max_power", [10.0, 10.0]),
                ("pricing", "price", [0.2, 0.2]),
            ]
        },
        "expected_outputs": {
            "segment_names": ["power_limit", "pricing"],
            "segment_types": ["PowerLimitSegment", "PricingSegment"],
            "segment_types_by_index": ["PowerLimitSegment", "PricingSegment"],
            "power_limit_max_power": [10.0, 10.0],
            "pricing_price": [0.2, 0.2],
        },
    },
    {
        "description": "Connection efficiency with pricing chains correctly",
        "periods": np.array([1.0, 1.0]),
        "segments": {
            "efficiency": {"segment_type": "efficiency", "efficiency": np.array([0.90, 0.90])},
            "pricing": {"segment_type": "pricing", "price": np.array([0.10, 0.10])},
        },
        "inputs": {"power_in": [10.0, 10.0], "minimize_cost": True},
        "expected_outputs": {"objective_value": 1.8, "power_out": [9.0, 9.0]},
    },
]
