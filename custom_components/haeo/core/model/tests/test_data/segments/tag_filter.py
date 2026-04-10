"""Tag filter segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.core.model.elements.segments import TagFilterSegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Tag filter blocks source-to-target flow",
        "factory": TagFilterSegment,
        "spec": {
            "segment_type": "tag_filter",
            "tag": "grid_import",
            "max_power_source_target": 0.0,
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {
            "maximize": {"power_out_st": 1.0},
        },
        "expected_outputs": {
            "power_out_st": (0.0, 0.0),
        },
    },
    {
        "description": "Tag filter limits source-to-target flow",
        "factory": TagFilterSegment,
        "spec": {
            "segment_type": "tag_filter",
            "tag": "solar",
            "max_power_source_target": np.array([5.0, 3.0]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {
            "maximize": {"power_out_st": 1.0},
        },
        "expected_outputs": {
            "power_out_st": (5.0, 3.0),
        },
    },
    {
        "description": "Tag filter limits target-to-source flow",
        "factory": TagFilterSegment,
        "spec": {
            "segment_type": "tag_filter",
            "tag": "battery",
            "max_power_target_source": np.array([2.0, 2.0]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {
            "maximize": {"power_out_ts": 1.0},
        },
        "expected_outputs": {
            "power_out_ts": (2.0, 2.0),
        },
    },
    {
        "description": "Tag filter with no limits allows unconstrained flow",
        "factory": TagFilterSegment,
        "spec": {
            "segment_type": "tag_filter",
            "tag": "solar",
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {
            "power_in_st": [10.0, 10.0],
        },
        "expected_outputs": {
            "power_out_st": (10.0, 10.0),
        },
    },
]
