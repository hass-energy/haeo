"""Adapter mapping cases for the load element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.load import LOAD_DEVICE_LOAD, LOAD_FORECAST_LIMIT_PRICE, LOAD_POWER
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    connection,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.load import LoadConfigData

from . import CreateCase, OutputsCase

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Load with forecast",
        "data": LoadConfigData(
            element_type=ElementType.LOAD,
            name="load_main",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.0, 2.0])},
            curtailment={},
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "load_main", "is_source": False, "is_sink": True},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "load_main:connection",
                "source": "network",
                "target": "load_main",
                "is_time_sensitive": True,
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [1.0, 2.0], "fixed": True},
                },
            },
        ],
    },
    {
        "description": "Sheddable load",
        "data": LoadConfigData(
            element_type=ElementType.LOAD,
            name="load_sheddable",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.0, 2.0])},
            curtailment={"curtailment": True},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": "load_sheddable",
                "is_source": False,
                "is_sink": True,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "load_sheddable:connection",
                "source": "network",
                "target": "load_sheddable",
                "is_time_sensitive": True,
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [1.0, 2.0], "fixed": False},
                },
            },
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Load with forecast",
        "data": LoadConfigData(
            element_type=ElementType.LOAD,
            name="load_main",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.0, 2.0])},
            curtailment={},
        ),
        "model_outputs": {
            "load_main:connection": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,))
                    }
                },
            }
        },
        "periods": np.array([1.0]),
        "outputs": {
            LOAD_DEVICE_LOAD: {
                LOAD_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-", fixed=True),
                LOAD_FORECAST_LIMIT_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,)),
            }
        },
    },
    {
        "description": "Load connection pruned - load carries no flow",
        "data": LoadConfigData(
            element_type=ElementType.LOAD,
            name="load_main",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.0, 2.0])},
            curtailment={},
        ),
        "model_outputs": {},
        "periods": np.array([1.0, 1.0]),
        "outputs": {
            LOAD_DEVICE_LOAD: {
                LOAD_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(0.0, 0.0), direction="-", fixed=True),
            }
        },
    },
]
