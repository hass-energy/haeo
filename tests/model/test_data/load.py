"""Test data and factories for Load element."""

from custom_components.haeo.model.load import Load

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Load with varying consumption",
        "factory": Load,
        "data": {
            "name": "load",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [1.0, 1.5, 2.0],
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (1.0, 1.5, 2.0)},
        },
    },
    {
        "description": "Load with zero consumption",
        "factory": Load,
        "data": {
            "name": "load_zero",
            "period": 1.0,
            "n_periods": 2,
            "forecast": [0.0, 0.0],
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Load with high consumption",
        "factory": Load,
        "data": {
            "name": "load_high",
            "period": 1.0,
            "n_periods": 4,
            "forecast": [10.0, 15.0, 12.0, 8.0],
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (10.0, 15.0, 12.0, 8.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = [
    {
        "description": "Load with forecast length mismatch",
        "factory": Load,
        "data": {
            "name": "load_mismatch",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [1.0, 1.5],  # Only 2 instead of 3
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
    {
        "description": "Load with forecast length mismatch (single value broadcast)",
        "factory": Load,
        "data": {
            "name": "load_broadcast_attempt",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [1.0],  # Length 1, not allowed
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
]
