"""Adapter mapping cases for the deferrable load element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.deferrable_load import (
    DEFERRABLE_ENERGY_DELIVERED,
    DEFERRABLE_ENERGY_OVERAGE,
    DEFERRABLE_ENERGY_SHORTFALL,
    DEFERRABLE_LOAD_DEVICE,
    DEFERRABLE_POWER,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
    connection,
)
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_OVERAGE,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.deferrable_load import DeferrableLoadConfigData

from . import CreateCase, OutputsCase


def _pump() -> DeferrableLoadConfigData:
    """Return a 2 kW pump whose 6 kWh window opened before the horizon and is due at boundary 3.

    Its meter has counted 2 kWh since the window opened, so 4 kWh remain.
    """
    return DeferrableLoadConfigData(
        element_type=ElementType.DEFERRABLE_LOAD,
        name="pump",
        connection=as_connection_target("home"),
        schedule={
            "in_window": np.array([1.0, 1.0, 1.0, 0.0]),
            "window_start": np.zeros(5),
            "opened": np.array([6.0, 0.0, 0.0, 0.0, 0.0]),
            "due": np.array([0.0, 0.0, 0.0, 6.0, 0.0]),
            "energy_meter": 2.0,
        },
        pricing={"deficit_price": np.full(5, 10.0), "overage_price": np.array([0.1, 0.2, 0.3, 0.4, 0.5])},
        power={"max_power": 2.0},
    )


def _heater() -> DeferrableLoadConfigData:
    """Return a heater without a power limit or meter whose 6 kWh window covers period 2."""
    return DeferrableLoadConfigData(
        element_type=ElementType.DEFERRABLE_LOAD,
        name="heater",
        connection=as_connection_target("home"),
        schedule={
            "in_window": np.array([0.0, 0.0, 1.0, 0.0]),
            "window_start": np.array([0.0, 0.0, 1.0, 0.0, 0.0]),
            "opened": np.array([0.0, 0.0, 6.0, 0.0, 0.0]),
            "due": np.array([0.0, 0.0, 0.0, 6.0, 0.0]),
        },
        pricing={"deficit_price": np.full(5, 10.0), "overage_price": np.zeros(5)},
    )


CREATE_CASES: list[CreateCase] = [
    {
        "description": "Deferrable load with a power limit and a meter seeding its open window",
        "data": _pump(),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
                "name": "pump",
                "is_source": False,
                "is_sink": True,
                "in_window": [1.0, 1.0, 1.0, 0.0],
                "window_start": [0.0, 0.0, 0.0, 0.0, 0.0],
                "opened": [6.0, 0.0, 0.0, 0.0, 0.0],
                "due": [0.0, 0.0, 0.0, 6.0, 0.0],
                "initial_energy": 2.0,
                "deficit_price": [10.0, 10.0, 10.0, 10.0, 10.0],
                "overage_price": [0.1, 0.2, 0.3, 0.4, 0.5],
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "pump:connection",
                "source": "home",
                "target": "pump",
                "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 2.0}},
            },
        ],
    },
    {
        "description": "Deferrable load without a power limit or meter gates itself to its windows",
        "data": _heater(),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
                "name": "heater",
                "is_source": False,
                "is_sink": True,
                "in_window": [0.0, 0.0, 1.0, 0.0],
                "window_start": [0.0, 0.0, 1.0, 0.0, 0.0],
                "opened": [0.0, 0.0, 6.0, 0.0, 0.0],
                "due": [0.0, 0.0, 0.0, 6.0, 0.0],
                "initial_energy": 0.0,
                "deficit_price": [10.0, 10.0, 10.0, 10.0, 10.0],
                "overage_price": [0.0, 0.0, 0.0, 0.0, 0.0],
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "heater:connection",
                "source": "home",
                "target": "heater",
                "segments": {},
            },
        ],
    },
]


def _energy(*values: float) -> OutputData:
    return OutputData(type=OutputType.ENERGY, unit="kWh", values=values)


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Deferrable load draws the 4 kWh its window still needs at its 2 kW limit",
        "data": _pump(),
        "model_outputs": {
            "pump": {
                DEFERRABLE_LOAD_ENERGY_DELIVERED: _energy(2.0, 4.0, 6.0, 6.0, 6.0),
                DEFERRABLE_LOAD_ENERGY_SHORTFALL: _energy(0.0, 0.0, 0.0, 0.0, 0.0),
                DEFERRABLE_LOAD_ENERGY_OVERAGE: _energy(0.0, 0.0, 0.0, 0.0, 0.0),
            },
            "pump:connection": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(2.0, 2.0, 0.0, 0.0), direction="+"
                ),
            },
        },
        "periods": np.ones(4),
        "outputs": {
            DEFERRABLE_LOAD_DEVICE: {
                DEFERRABLE_POWER: OutputData(
                    type=OutputType.POWER, unit="kW", values=(2.0, 2.0, 0.0, 0.0), direction="-"
                ),
                DEFERRABLE_ENERGY_DELIVERED: _energy(2.0, 4.0, 6.0, 6.0, 6.0),
                DEFERRABLE_ENERGY_SHORTFALL: _energy(0.0, 0.0, 0.0, 0.0, 0.0),
                DEFERRABLE_ENERGY_OVERAGE: _energy(0.0, 0.0, 0.0, 0.0, 0.0),
            }
        },
    },
    {
        "description": "Deferrable load connection pruned - nothing drawn, so the remainder falls short",
        "data": _pump(),
        "model_outputs": {
            "pump": {
                DEFERRABLE_LOAD_ENERGY_DELIVERED: _energy(2.0, 2.0, 2.0, 2.0, 2.0),
                DEFERRABLE_LOAD_ENERGY_SHORTFALL: _energy(0.0, 0.0, 0.0, 4.0, 0.0),
                DEFERRABLE_LOAD_ENERGY_OVERAGE: _energy(0.0, 0.0, 0.0, 0.0, 0.0),
            },
        },
        "periods": np.ones(4),
        "outputs": {
            DEFERRABLE_LOAD_DEVICE: {
                DEFERRABLE_POWER: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.0, 0.0, 0.0, 0.0), direction="-"
                ),
                DEFERRABLE_ENERGY_DELIVERED: _energy(2.0, 2.0, 2.0, 2.0, 2.0),
                DEFERRABLE_ENERGY_SHORTFALL: _energy(0.0, 0.0, 0.0, 4.0, 0.0),
                DEFERRABLE_ENERGY_OVERAGE: _energy(0.0, 0.0, 0.0, 0.0, 0.0),
            }
        },
    },
]
