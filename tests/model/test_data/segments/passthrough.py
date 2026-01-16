"""Passthrough segment scenarios."""

from collections.abc import Sequence

from custom_components.haeo.model.elements.segments import PassthroughSegment

from ..segment_types import SegmentScenario


SCENARIOS: Sequence[SegmentScenario] = [
    {
        "description": "Passthrough forwards power unchanged",
        "factory": PassthroughSegment,
        "spec": {"segment_type": "passthrough"},
        "periods": [1.0, 1.0],
        "inputs": {"power_in_st": [4.0, 6.0], "power_in_ts": [1.0, 2.0]},
        "expected_outputs": {
            "power_out_st": [4.0, 6.0],
            "power_out_ts": [1.0, 2.0],
        },
    },
]
