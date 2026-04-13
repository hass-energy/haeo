"""Passthrough segment scenarios."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.core.model.elements.segments import PassthroughSegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Passthrough forwards power unchanged",
        "factory": PassthroughSegment,
        "spec": {"segment_type": "passthrough"},
        "periods": np.array([1.0, 1.0]),
        "inputs": {"power_in": [4.0, 6.0]},
        "expected_outputs": {
            "power_out": [4.0, 6.0],
        },
    },
]
