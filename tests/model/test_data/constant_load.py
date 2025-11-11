"""Test data and factories for ConstantLoad element."""

from typing import Any

from custom_components.haeo.model.constant_load import ConstantLoad


def create(data: dict[str, Any]) -> ConstantLoad:
    """Create a test ConstantLoad instance."""
    return ConstantLoad(**data)


VALID_CASES = [
    {
        "description": "Constant load with fixed power",
        "factory": create,
        "data": {
            "name": "constant_load",
            "period": 1.0,
            "n_periods": 2,
            "power": 1.5,
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (1.5, 1.5)},
        },
    },
]

INVALID_CASES: list[dict[str, Any]] = []
