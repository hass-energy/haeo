"""Test data and factories for base Element class."""

from typing import Any

from custom_components.haeo.model.element import Element

from . import lp_sequence


def create(**data: Any) -> Element:
    """Create a test Element instance with fixed values.

    Note: Element is the abstract base class. These tests verify basic
    functionality using fixed LP variables. Concrete element tests use
    real optimization scenarios.
    """
    # Remove power_setup if present (not used for base Element tests)
    data.pop("power_setup", None)

    # Extract optional price fields if not provided
    element_data = {
        "power_consumption": lp_sequence("consumption", data["n_periods"]),
        "power_production": lp_sequence("production", data["n_periods"]),
        "energy": lp_sequence("energy", data["n_periods"]),
        **data,
    }

    return Element(**element_data)


VALID_CASES = [
    {
        "description": "Base element with power and energy",
        "factory": create,
        "data": {
            "name": "element",
            "period": 1.0,
            "n_periods": 2,
            "price_consumption": (0.25, 0.35),
            "price_production": (0.15, 0.1),
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (1.0, 2.0)},
            "price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.25, 0.35)},
            "price_production": {"type": "price", "unit": "$/kWh", "values": (0.15, 0.1)},
        },
    }
]

INVALID_CASES: list[dict[str, Any]] = []
