"""Adapter mapping cases for the solar element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.solar import SOLAR_DEVICE_SOLAR, SOLAR_FORECAST_LIMIT, SOLAR_POWER
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    connection,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.solar import SolarConfigData

from . import CreateCase, OutputsCase

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Solar with production price",
        "data": SolarConfigData(
            {
                "element_type": ElementType.SOLAR,
                "name": "pv_main",
                "connection": as_connection_target("network"),
                "forecast": {
                    "forecast": np.array([2.0, 1.5]),
                },
                "curtailment": {
                    "curtailment": False,
                },
            }
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "pv_main", "is_source": True, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "pv_main:connection",
                "source": "pv_main",
                "target": "network",
                "is_time_sensitive": True,
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": [2.0, 1.5],
                        "fixed": True,
                    },
                },
            },
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Solar with forecast limit",
        "data": SolarConfigData(
            element_type=ElementType.SOLAR,
            name="pv_main",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([2.0])},
            curtailment={"curtailment": True},
        ),
        "model_outputs": {
            "pv_main:connection": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.02,))
                    }
                },
            }
        },
        "periods": np.array([1.0]),
        "outputs": {
            SOLAR_DEVICE_SOLAR: {
                SOLAR_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="+"),
                SOLAR_FORECAST_LIMIT: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.02,)),
            }
        },
    },
    {
        "description": "Solar with shadow price output",
        "data": SolarConfigData(
            element_type=ElementType.SOLAR,
            name="pv_with_price",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.5])},
            curtailment={"curtailment": True},
        ),
        "model_outputs": {
            "pv_with_price:connection": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(1.5,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,))
                    }
                },
            }
        },
        "periods": np.array([1.0]),
        "outputs": {
            SOLAR_DEVICE_SOLAR: {
                SOLAR_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(1.5,), direction="+"),
                SOLAR_FORECAST_LIMIT: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            }
        },
    },
    {
        "description": "Solar connection pruned - solar carries no flow",
        "data": SolarConfigData(
            element_type=ElementType.SOLAR,
            name="pv_main",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([2.0, 3.0])},
            curtailment={"curtailment": True},
        ),
        "model_outputs": {},
        "periods": np.array([1.0, 1.0]),
        "outputs": {
            SOLAR_DEVICE_SOLAR: {
                SOLAR_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(0.0, 0.0), direction="+"),
            }
        },
    },
]
