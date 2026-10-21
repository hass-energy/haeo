"""Adapter mapping cases for the deferrable load element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.deferrable_load import (
    DEFERRABLE_ENERGY_DELIVERED,
    DEFERRABLE_ENERGY_OVERAGE,
    DEFERRABLE_ENERGY_SHORTFALL,
    DEFERRABLE_LOAD_DEVICE,
    DEFERRABLE_POWER,
)
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
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
from custom_components.haeo.core.schema.elements.deferrable_load import DeferrableLoadConfigData, ScheduleData

from . import CreateCase, OutputsCase

# A 6 kWh window over period 2 of a four-period horizon
SCHEDULE: ScheduleData = {
    "in_window": np.array([0.0, 0.0, 1.0, 0.0]),
    "window_start": np.array([0.0, 0.0, 1.0, 0.0, 0.0]),
    "opened": np.array([0.0, 0.0, 6.0, 0.0, 0.0]),
    "due": np.array([0.0, 0.0, 0.0, 6.0, 0.0]),
}
OVERAGE_PRICE = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

PUMP = DeferrableLoadConfigData(
    element_type=ElementType.DEFERRABLE_LOAD,
    name="pump",
    connection=as_connection_target("home"),
    schedule={**SCHEDULE, "energy_meter": 2.0},
    pricing={"deficit_price": np.full(5, 10.0), "overage_price": OVERAGE_PRICE},
    power={"max_power": 1.5},
)


def _load_element(name: str, *, initial_energy: float) -> dict[str, object]:
    """Return the deferrable load model element built from SCHEDULE and the pricing above."""
    return {
        "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
        "name": name,
        "is_source": False,
        "is_sink": True,
        **SCHEDULE,
        "initial_energy": initial_energy,
        "deficit_price": [10.0] * 5,
        "overage_price": OVERAGE_PRICE,
    }


CREATE_CASES: list[CreateCase] = [
    {
        "description": "Deferrable load with a power limit, meter, and overage price",
        "data": PUMP,
        "model": [
            _load_element("pump", initial_energy=2.0),
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "pump:connection",
                "source": "home",
                "target": "pump",
                "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 1.5}},
            },
        ],
    },
    {
        "description": "Deferrable load without a power limit or meter gates itself to its windows",
        "data": DeferrableLoadConfigData(
            element_type=ElementType.DEFERRABLE_LOAD,
            name="unlimited",
            connection=as_connection_target("home"),
            schedule=SCHEDULE,
            pricing={"deficit_price": np.full(5, 10.0), "overage_price": OVERAGE_PRICE},
        ),
        "model": [
            _load_element("unlimited", initial_energy=0.0),
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "unlimited:connection",
                "source": "home",
                "target": "unlimited",
                "segments": {},
            },
        ],
    },
]

DELIVERED = OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0, 0.0, 0.0, 6.0, 6.0))
SHORTFALL = OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0, 0.0, 0.0, 0.0, 0.0))
OVERAGE = OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0, 0.0, 0.0, 0.5, 0.0))

LOAD_OUTPUTS: dict[ModelOutputName, ModelOutputValue] = {
    DEFERRABLE_LOAD_ENERGY_DELIVERED: DELIVERED,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL: SHORTFALL,
    DEFERRABLE_LOAD_ENERGY_OVERAGE: OVERAGE,
}

OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Deferrable load reports the power it draws and its window energy",
        "data": PUMP,
        "model_outputs": {
            "pump": LOAD_OUTPUTS,
            "pump:connection": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.0, 0.0, 6.0, 0.0), direction="+"
                ),
            },
        },
        "periods": np.ones(4),
        "outputs": {
            DEFERRABLE_LOAD_DEVICE: {
                DEFERRABLE_POWER: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.0, 0.0, 6.0, 0.0), direction="-"
                ),
                DEFERRABLE_ENERGY_DELIVERED: DELIVERED,
                DEFERRABLE_ENERGY_SHORTFALL: SHORTFALL,
                DEFERRABLE_ENERGY_OVERAGE: OVERAGE,
            }
        },
    },
    {
        "description": "Deferrable load connection pruned - load draws no power",
        "data": PUMP,
        "model_outputs": {"pump": LOAD_OUTPUTS},
        "periods": np.ones(4),
        "outputs": {
            DEFERRABLE_LOAD_DEVICE: {
                DEFERRABLE_POWER: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.0, 0.0, 0.0, 0.0), direction="-"
                ),
                DEFERRABLE_ENERGY_DELIVERED: DELIVERED,
                DEFERRABLE_ENERGY_SHORTFALL: SHORTFALL,
                DEFERRABLE_ENERGY_OVERAGE: OVERAGE,
            }
        },
    },
]
