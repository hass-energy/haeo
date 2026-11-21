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
    segments=[],
)

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Connection with segments, in the order listed",
        "data": ConnectionConfigData(
            element_type=ElementType.CONNECTION,
            name="conn",
            endpoints={"source": as_connection_target("s"), "target": as_connection_target("t")},
            segments=[
                {"segment_type": "efficiency", "efficiency": np.array([0.95])},
                {"segment_type": "power_limit", "max_power": np.array([4.0])},
                {"segment_type": "pricing", "price": np.array([0.1])},
                {"segment_type": "power_limit", "max_power": np.array([3.0])},
            ],
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn",
                "source": "s",
                "target": "t",
                "segments": {
                    "0_efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                    "1_power_limit": {"segment_type": "power_limit", "max_power": [4.0]},
                    "2_pricing": {"segment_type": "pricing", "price": [0.1]},
                    "3_power_limit": {"segment_type": "power_limit", "max_power": [3.0]},
                },
            },
        ],
    },
    {
        "description": "Connection with no segments",
        "data": MINIMAL,
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn_min",
                "source": "s",
                "target": "t",
                "segments": {},
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
