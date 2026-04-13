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
            "efficiency": np.array([0.9, 0.9]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {"power_in": [10.0, 10.0]},
        "expected_outputs": {
            "power_out": [9.0, 9.0],
        },
    },
]
