"""Power limit segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.core.model.elements.segments import PowerLimitSegment
from custom_components.haeo.core.model.elements.segments.power_limit import SHORTFALL_PRICE

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Power limit caps source-to-target flow",
        "factory": PowerLimitSegment,
        "spec": {"segment_type": "power_limit", "max_power": np.array([5.0, 5.0])},
        "periods": np.array([1.0, 1.0]),
        "inputs": {"maximize": {"power_in": 1.0}},
        "expected_outputs": {"power_in": [5.0, 5.0], "power_out": [5.0, 5.0]},
    },
    {
        "description": "Power limit caps target-to-source flow",
        "factory": PowerLimitSegment,
        "spec": {"segment_type": "power_limit", "max_power": np.array([3.0, 3.0])},
        "periods": np.array([1.0, 1.0]),
        "inputs": {"maximize": {"power_in": 1.0}},
        "expected_outputs": {"power_in": [3.0, 3.0], "power_out": [3.0, 3.0]},
    },
    {
        "description": "Fixed power limits hold the flow at the limit when it can reach it",
        "factory": PowerLimitSegment,
        "spec": {
            "segment_type": "power_limit",
            "max_power": np.array([5.0, 5.0]),
            "fixed": True,
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {"power_in": [5.0, 5.0]},
    },
    {
        "description": "Fixed power limits fall short at the shortfall price when the flow cannot reach them",
        "factory": PowerLimitSegment,
        "spec": {
            "segment_type": "power_limit",
            "max_power": np.array([5.0, 5.0]),
            "fixed": True,
        },
        "periods": np.array([1.0, 0.5]),
        "inputs": {"power_in": [3.0, 5.0], "minimize_cost": True},
        "expected_outputs": {"power_in": [3.0, 5.0], "objective_value": 2.0 * SHORTFALL_PRICE},
    },
]
