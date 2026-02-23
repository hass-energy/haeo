"""Efficiency segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.core.model.elements.segments import EfficiencySegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Efficiency scales output power",
        "factory": EfficiencySegment,
        "spec": {
            "segment_type": "efficiency",
            "efficiency_source_target": np.array([0.9, 0.9]),
            "efficiency_target_source": np.array([0.95, 0.95]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {"power_in_st": [10.0, 10.0], "power_in_ts": [10.0, 10.0]},
        "expected_outputs": {
            "power_out_st": [9.0, 9.0],
            "power_out_ts": [9.5, 9.5],
        },
    },
]
