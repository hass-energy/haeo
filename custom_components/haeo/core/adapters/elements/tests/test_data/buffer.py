"""Adapter mapping cases for the buffer element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.buffer import (
    BUFFER_DEVICE_BUFFER,
    BUFFER_ENERGY_AVAILABLE,
    BUFFER_ENERGY_REQUIRED,
    BUFFER_ENERGY_SHORTFALL,
    BUFFER_STATE_OF_CHARGE,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BUFFER
from custom_components.haeo.core.model.elements import buffer as model_buffer
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import BufferConfigData

from . import CreateCase, OutputsCase

RESERVE = BufferConfigData(
    element_type=ElementType.BUFFER,
    name="reserve",
    kind="reserve",
    participants={"loads": ["house"], "generation": ["solar"], "storage": ["battery"]},
    requirement={"window": 2.0, "level": np.array([0.2, 0.2])},
    pricing={"shortfall_cost": np.array([10.0])},
)

ENERGY_REQUIRED = OutputData(type=OutputType.ENERGY, unit="kWh", values=(2.0, 1.0))
ENERGY_AVAILABLE = OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0))
ENERGY_SHORTFALL = OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0, 0.5))
STATE_OF_CHARGE = OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.4, 0.3), direction="+")

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Reserve names its participants and passes its level on",
        "data": RESERVE,
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BUFFER,
                "name": "reserve",
                "kind": "reserve",
                "loads": ["house"],
                "generation": ["solar"],
                "storage": ["battery"],
                "window": 2.0,
                "level": [0.2, 0.2],
                "price": [10.0],
            }
        ],
    },
    {
        "description": "Headroom without a level or optional participants",
        "data": BufferConfigData(
            element_type=ElementType.BUFFER,
            name="headroom",
            kind="headroom",
            participants={"storage": ["battery"]},
            requirement={"window": 4.0},
            pricing={"shortfall_cost": 5.0},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BUFFER,
                "name": "headroom",
                "kind": "headroom",
                "loads": [],
                "generation": [],
                "storage": ["battery"],
                "window": 4.0,
                "level": None,
                "price": 5.0,
            }
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Buffer reports its requirement, availability, shortfall, and level",
        "data": RESERVE,
        "model_outputs": {
            "reserve": {
                model_buffer.BUFFER_ENERGY_REQUIRED: ENERGY_REQUIRED,
                model_buffer.BUFFER_ENERGY_AVAILABLE: ENERGY_AVAILABLE,
                model_buffer.BUFFER_ENERGY_SHORTFALL: ENERGY_SHORTFALL,
                model_buffer.BUFFER_STATE_OF_CHARGE: STATE_OF_CHARGE,
            }
        },
        "periods": np.array([1.0]),
        "outputs": {
            BUFFER_DEVICE_BUFFER: {
                BUFFER_ENERGY_REQUIRED: ENERGY_REQUIRED,
                BUFFER_ENERGY_AVAILABLE: ENERGY_AVAILABLE,
                BUFFER_ENERGY_SHORTFALL: ENERGY_SHORTFALL,
                BUFFER_STATE_OF_CHARGE: STATE_OF_CHARGE,
            }
        },
    },
]
