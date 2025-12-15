"""Test data and factories for SourceSink element."""

from custom_components.haeo.model.source_sink import SourceSink

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "SourceSink junction with no flow",
        "factory": SourceSink,
        "data": {
            "name": "junction",
            "periods": [1.0] * 3,
            "is_source": False,
            "is_sink": False,
        },
        "inputs": {"power": [0.0, 0.0, 0.0]},
        "expected_outputs": {
            "source_sink_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "SourceSink sink-only consumes power",
        "factory": SourceSink,
        "data": {
            "name": "sink_only",
            "periods": [1.0] * 3,
            "is_source": False,
            "is_sink": True,
        },
        "inputs": {"power": [2.0, 0.5, 1.5]},
        "expected_outputs": {
            "source_sink_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "SourceSink source-only exports power",
        "factory": SourceSink,
        "data": {
            "name": "source_only",
            "periods": [1.0] * 3,
            "is_source": True,
            "is_sink": False,
        },
        "inputs": {"power": [-1.0, -0.5, 0.0]},
        "expected_outputs": {
            "source_sink_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "SourceSink bidirectional balances import and export",
        "factory": SourceSink,
        "data": {
            "name": "bidirectional",
            "periods": [1.0] * 3,
            "is_source": True,
            "is_sink": True,
        },
        "inputs": {"power": [0.5, -1.5, 0.0]},
        "expected_outputs": {},
    },
]

INVALID_CASES: list[ElementTestCase] = []
