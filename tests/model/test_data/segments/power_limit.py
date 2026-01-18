"""Power limit segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.model.elements.segments import PowerLimitSegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Power limit caps source-to-target flow",
        "factory": PowerLimitSegment,
        "spec": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0])},
        "periods": np.array([1.0, 1.0]),
        "inputs": {"maximize": {"power_in_st": 1.0}},
        "expected_outputs": {"power_in_st": [5.0, 5.0], "power_out_st": [5.0, 5.0]},
    },
    {
        "description": "Power limit caps target-to-source flow",
        "factory": PowerLimitSegment,
        "spec": {"segment_type": "power_limit", "max_power_target_source": np.array([3.0, 3.0])},
        "periods": np.array([1.0, 1.0]),
        "inputs": {"maximize": {"power_in_ts": 1.0}},
        "expected_outputs": {"power_in_ts": [3.0, 3.0], "power_out_ts": [3.0, 3.0]},
    },
    {
        "description": "Fixed power limits enforce equality",
        "factory": PowerLimitSegment,
        "spec": {
            "segment_type": "power_limit",
            "max_power_source_target": np.array([5.0, 5.0]),
            "fixed": True,
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {},
        "expected_outputs": {"power_in_st": [5.0, 5.0]},
    },
    {
        "description": "Time-slice constraint limits bidirectional flow",
        "factory": PowerLimitSegment,
        "spec": {
            "segment_type": "power_limit",
            "max_power_source_target": np.array([10.0]),
            "max_power_target_source": np.array([10.0]),
        },
        "periods": np.array([1.0]),
        "inputs": {"maximize": {"power_in_st": 1.0, "power_in_ts": 0.5}},
        "expected_outputs": {"power_in_st": [10.0], "power_in_ts": [0.0]},
    },
]
