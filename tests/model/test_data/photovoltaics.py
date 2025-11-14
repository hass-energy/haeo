"""Test data and factories for Photovoltaics element."""

from typing import Any

from pulp import LpVariable

from custom_components.haeo.model.photovoltaics import Photovoltaics

from . import fix_lp_variable


def create(data: dict[str, Any]) -> Photovoltaics:
    """Create a test Photovoltaics instance with fixed values."""

    pv = Photovoltaics(**data)

    if pv.power_production is not None:
        for variable, value in zip(pv.power_production, pv.forecast, strict=False):
            if isinstance(variable, LpVariable):
                fix_lp_variable(variable, value)

    return pv


VALID_CASES = [
    {
        "description": "Photovoltaics with valid forecast",
        "factory": create,
        "data": {
            "name": "pv",
            "period": 1.0,
            "n_periods": 2,
            "forecast": [1.2, 1.4],
        },
        "expected_outputs": {
            "power_available": {"type": "power", "unit": "kW", "values": (1.2, 1.4)},
            "power_produced": {"type": "power", "unit": "kW", "values": (1.2, 1.4)},
        },
    },
]

INVALID_CASES = [
    {
        "description": "Photovoltaics with forecast length mismatch",
        "element_class": Photovoltaics,
        "data": {
            "name": "photovoltaics",
            "period": 1.0,
            "n_periods": 2,
            "forecast": (1.2,),  # Only 1 instead of 2
            "price_production": (0.1, 0.2),
            "price_consumption": (0.3, 0.4),
        },
        "expected_error": "forecast length",
    },
    {
        "description": "Photovoltaics with price_production length mismatch",
        "element_class": Photovoltaics,
        "data": {
            "name": "photovoltaics",
            "period": 1.0,
            "n_periods": 2,
            "forecast": (1.2, 1.4),
            "price_production": (0.1,),  # Only 1 instead of 2
            "price_consumption": (0.3, 0.4),
        },
        "expected_error": "price_production length",
    },
    {
        "description": "Photovoltaics with price_consumption length mismatch",
        "element_class": Photovoltaics,
        "data": {
            "name": "photovoltaics",
            "period": 1.0,
            "n_periods": 2,
            "forecast": (1.2, 1.4),
            "price_production": (0.1, 0.2),
            "price_consumption": (0.3,),  # Only 1 instead of 2
        },
        "expected_error": "price_consumption length",
    },
]
