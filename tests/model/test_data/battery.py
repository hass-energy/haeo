"""Test data and factories for Battery element."""

from typing import Any

from pulp import LpVariable

from custom_components.haeo.model.battery import Battery

from . import fix_lp_variable


def create(data: dict[str, Any]) -> Battery:
    """Create a test Battery instance with fixed values."""

    battery = Battery(**data)

    if battery.power_consumption is not None:
        for index, variable in enumerate(battery.power_consumption):
            if isinstance(variable, LpVariable):
                fix_lp_variable(variable, float(index + 1))
    if battery.power_production is not None:
        for index, variable in enumerate(battery.power_production):
            if isinstance(variable, LpVariable):
                fix_lp_variable(variable, float(index + 1))
    if battery.energy is not None:
        for variable in battery.energy[1:]:
            if isinstance(variable, LpVariable):
                fix_lp_variable(variable, 6.0)

    return battery


VALID_CASES = [
    {
        "description": "Battery with full configuration",
        "factory": create,
        "data": {
            "name": "battery",
            "period": 1.0,
            "n_periods": 2,
            "capacity": [10.0, 10.0],
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 25.0,
            "max_charge_percentage": 90.0,
            "efficiency": 0.95,
            "charge_cost": 0.2,
            "discharge_cost": 0.1,
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 6.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 60.0)},
            "price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.0, 0.2)},
            "price_production": {"type": "price", "unit": "$/kWh", "values": (0.1, 0.1)},
        },
    },
]

INVALID_CASES: list[dict[str, Any]] = []
