"""Adapter mapping cases for the inverter element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.inverter import (
    INVERTER_DC_BUS_POWER_BALANCE,
    INVERTER_DEVICE_INVERTER,
    INVERTER_MAX_POWER_AC_TO_DC_PRICE,
    INVERTER_MAX_POWER_DC_TO_AC_PRICE,
    INVERTER_POWER_AC_TO_DC,
    INVERTER_POWER_ACTIVE,
    INVERTER_POWER_DC_TO_AC,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    connection,
)
from custom_components.haeo.core.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.inverter import InverterConfigData

from . import CreateCase, OutputsCase

MAIN = InverterConfigData(
    element_type=ElementType.INVERTER,
    name="inverter_main",
    connection=as_connection_target("network"),
    power_limits={
        "max_power_source_target": np.array([10.0]),
        "max_power_target_source": np.array([8.0]),
    },
    efficiency={
        "efficiency_source_target": np.array(1.0),
        "efficiency_target_source": np.array(1.0),
    },
)

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Inverter with efficiency",
        "data": MAIN,
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "inverter_main", "is_source": False, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_main:dc_to_ac",
                "source": "inverter_main",
                "target": "network",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                    "power_limit": {"segment_type": "power_limit", "max_power": [10.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_main:ac_to_dc",
                "source": "network",
                "target": "inverter_main",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [8.0]},
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                },
            },
        ],
    },
    {
        "description": "Inverter with default efficiency (100%)",
        "data": InverterConfigData(
            element_type=ElementType.INVERTER,
            name="inverter_simple",
            connection=as_connection_target("network"),
            power_limits={
                "max_power_source_target": np.array([10.0]),
                "max_power_target_source": np.array([10.0]),
            },
            efficiency={
                "efficiency_source_target": np.array(1.0),
                "efficiency_target_source": np.array(1.0),
            },
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "inverter_simple", "is_source": False, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_simple:dc_to_ac",
                "source": "inverter_simple",
                "target": "network",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                    "power_limit": {"segment_type": "power_limit", "max_power": [10.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_simple:ac_to_dc",
                "source": "network",
                "target": "inverter_simple",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [10.0]},
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                },
            },
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Inverter with all outputs",
        "data": MAIN,
        "model_outputs": {
            "inverter_main": {
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "inverter_main:dc_to_ac": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,)),
                    }
                },
            },
            "inverter_main:ac_to_dc": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.02,)),
                    }
                },
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            INVERTER_DEVICE_INVERTER: {
                INVERTER_DC_BUS_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                INVERTER_POWER_DC_TO_AC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                INVERTER_POWER_AC_TO_DC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="-"
                ),
                INVERTER_POWER_ACTIVE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction=None),
                INVERTER_MAX_POWER_DC_TO_AC_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,)
                ),
                INVERTER_MAX_POWER_AC_TO_DC_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.02,)
                ),
            }
        },
    },
    {
        "description": "Inverter AC-to-DC connection pruned - rectifier carries no flow",
        "data": MAIN,
        "model_outputs": {
            "inverter_main": {
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "inverter_main:dc_to_ac": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,)),
                    }
                },
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            INVERTER_DEVICE_INVERTER: {
                INVERTER_DC_BUS_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                INVERTER_POWER_DC_TO_AC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                INVERTER_POWER_AC_TO_DC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.0,), direction="-"
                ),
                INVERTER_POWER_ACTIVE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction=None),
                INVERTER_MAX_POWER_DC_TO_AC_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,)
                ),
            }
        },
    },
]
