"""Adapter mapping cases for the connection element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.connection import CONNECTION_DEVICE_CONNECTION, CONNECTION_POWER
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements import connection as model_connection
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData

from . import CreateCase, OutputsCase

MINIMAL = ConnectionConfigData(
    element_type=ElementType.CONNECTION,
    name="conn_min",
    endpoints={"source": as_connection_target("s"), "target": as_connection_target("t")},
    power_limits={},
    efficiency={},
    pricing={},
)

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Connection with all optional fields",
        "data": ConnectionConfigData(
            element_type=ElementType.CONNECTION,
            name="conn",
            endpoints={"source": as_connection_target("s"), "target": as_connection_target("t")},
            power_limits={
                "max_power_source_target": np.array([4.0]),
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
            },
            pricing={
                "price_source_target": np.array([0.1]),
            },
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "s",
                "target": "t",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [4.0]},
                    "pricing": {"segment_type": "pricing", "price": [0.1]},
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                },
            },
        ],
    },
    {
        "description": "Connection with minimal fields",
        "data": MINIMAL,
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn_min",
                "source": "s",
                "target": "t",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": None},
                    "pricing": {"segment_type": "pricing", "price": None},
                    "efficiency": {"segment_type": "efficiency", "efficiency": None},
                },
            },
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Connection outputs",
        "data": MINIMAL,
        "model_outputs": {
            "conn_min": {
                model_connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            CONNECTION_DEVICE_CONNECTION: {
                CONNECTION_POWER: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
            }
        },
    },
]
