"""Adapter mapping cases for the EV element."""

from collections.abc import Mapping

import numpy as np

from custom_components.haeo.core.adapters.elements.ev import (
    EV_DEVICE_EV,
    EV_ENERGY_STORED,
    EV_POWER_ACTIVE,
    EV_POWER_CHARGE,
    EV_POWER_DISCHARGE,
    EV_POWER_MAX_CHARGE_PRICE,
    EV_STATE_OF_CHARGE,
    EV_TRIP_ENERGY_DELIVERED,
    EV_TRIP_ENERGY_SHORTFALL,
)
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
    connection,
)
from custom_components.haeo.core.model.elements import battery as model_battery
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import EvConfigData

from . import CreateCase, OutputsCase

# Home and plugged in for the first hour, then away on a 20 km trip in the second
EV = EvConfigData(
    element_type=ElementType.EV,
    name="ev",
    connection=as_connection_target("home"),
    vehicle={"capacity": np.full(3, 50.0), "energy_per_distance": 0.2, "current_soc": 0.1},
    charging={"max_charge_rate": 10.0, "connected": True},
    trip={
        "away": np.array([0.0, 1.0]),
        "trip_start": np.array([0.0, 1.0, 0.0]),
        "trip_opened": np.array([0.0, 20.0, 0.0]),
        "trip_due": np.array([0.0, 0.0, 20.0]),
    },
    public_charging={"public_charging_price": 0.6},
    efficiency={},
    advanced={"charge_limit_cost": 100.0},
)

CREATE_CASES: list[CreateCase] = [
    {
        "description": "EV pack, home charger, and trip load drawn while away",
        "data": EV,
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "ev",
                "capacity": [50.0, 50.0, 50.0],
                "initial_charge": 5.0,
                "salvage_value": 0.54,
                "charge_limit_cost": 100.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "ev:charge",
                "source": "home",
                "target": "ev",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [10.0, 0.0]},
                    "efficiency": {"segment_type": "efficiency", "efficiency": None},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "ev:discharge",
                "source": "ev",
                "target": "home",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": None},
                    "power_limit": {"segment_type": "power_limit", "max_power": [0.0, 0.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
                "name": "ev:trip",
                "is_source": False,
                "is_sink": True,
                "in_window": [0.0, 1.0],
                "window_start": [0.0, 1.0, 0.0],
                "opened": [0.0, 4.0, 0.0],
                "due": [0.0, 0.0, 4.0],
                "initial_energy": 0.0,
                "deficit_price": [0.6, 0.6, 0.6],
                "overage_price": [10.0, 10.0, 10.0],
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "ev:trip_connection",
                "source": "ev",
                "target": "ev:trip",
                "segments": {"power_limit": {"segment_type": "power_limit", "max_power": [0.0, 1e6]}},
            },
        ],
    },
]

ENERGY_STORED = OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 15.0, 11.0))
TRIP_DELIVERED = OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0, 0.0, 4.0))
TRIP_SHORTFALL = OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0, 0.0, 0.0))
CHARGE_LIMIT_PRICE = OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.05, 0.0))

PACK_AND_TRIP: dict[str, Mapping[ModelOutputName, ModelOutputValue]] = {
    "ev": {
        model_battery.BATTERY_ENERGY_STORED: ENERGY_STORED,
        model_battery.BATTERY_POWER_CHARGE: OutputData(
            type=OutputType.POWER, unit="kW", values=(10.0, 0.0), direction="-"
        ),
    },
    "ev:trip": {
        DEFERRABLE_LOAD_ENERGY_DELIVERED: TRIP_DELIVERED,
        DEFERRABLE_LOAD_ENERGY_SHORTFALL: TRIP_SHORTFALL,
    },
}

OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "EV charges at home then drives its trip",
        "data": EV,
        "model_outputs": {
            **PACK_AND_TRIP,
            "ev:charge": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(10.0, 0.0), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {"power_limit": {"power_limit": CHARGE_LIMIT_PRICE}},
            },
            "ev:discharge": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.0, 0.0), direction="+"
                ),
            },
        },
        "periods": np.ones(2),
        "outputs": {
            EV_DEVICE_EV: {
                EV_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(10.0, 0.0), direction="-"),
                EV_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.0, 0.0), direction="+"),
                EV_ENERGY_STORED: ENERGY_STORED,
                EV_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-10.0, 0.0), direction=None),
                EV_STATE_OF_CHARGE: OutputData(
                    type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.1, 0.3, 0.22), direction=None
                ),
                EV_TRIP_ENERGY_DELIVERED: TRIP_DELIVERED,
                EV_TRIP_ENERGY_SHORTFALL: TRIP_SHORTFALL,
                EV_POWER_MAX_CHARGE_PRICE: CHARGE_LIMIT_PRICE,
            }
        },
    },
    {
        "description": "EV home connections pruned - car neither charges nor discharges",
        "data": EV,
        "model_outputs": PACK_AND_TRIP,
        "periods": np.ones(2),
        "outputs": {
            EV_DEVICE_EV: {
                EV_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.0, 0.0), direction="-"),
                EV_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.0, 0.0), direction="+"),
                EV_ENERGY_STORED: ENERGY_STORED,
                EV_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(0.0, 0.0), direction=None),
                EV_STATE_OF_CHARGE: OutputData(
                    type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.1, 0.3, 0.22), direction=None
                ),
                EV_TRIP_ENERGY_DELIVERED: TRIP_DELIVERED,
                EV_TRIP_ENERGY_SHORTFALL: TRIP_SHORTFALL,
            }
        },
    },
]
