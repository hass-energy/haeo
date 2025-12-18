"""Test data for inverter element configuration."""

from collections.abc import Sequence

from custom_components.haeo.elements import inverter as inverter_element
from custom_components.haeo.model import connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import SOURCE_SINK_POWER_BALANCE

from .types import ElementConfigData, ElementConfigSchema, ElementValidCase, InvalidModelCase, InvalidSchemaCase

# Fully-typed pipeline cases
VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
    {
        "description": "Adapter mapping inverter case with efficiency",
        "element_type": "inverter",
        "schema": inverter_element.InverterConfigSchema(
            element_type="inverter",
            name="inverter_main",
            connection="network",
            max_power_dc_to_ac=["sensor.max_power"],
            max_power_ac_to_dc=["sensor.max_power"],
            efficiency_dc_to_ac=100,
            efficiency_ac_to_dc=100,
        ),
        "data": inverter_element.InverterConfigData(
            element_type="inverter",
            name="inverter_main",
            connection="network",
            max_power_dc_to_ac=[10.0],
            max_power_ac_to_dc=[10.0],
            efficiency_dc_to_ac=100.0,
            efficiency_ac_to_dc=100.0,
        ),
        "model": [
            {"element_type": "source_sink", "name": "inverter_main", "is_source": False, "is_sink": False},
            {
                "element_type": "connection",
                "name": "inverter_main:connection",
                "source": "inverter_main",
                "target": "network",
                "max_power_source_target": [10.0],
                "max_power_target_source": [10.0],
                "efficiency_source_target": 100.0,
                "efficiency_target_source": 100.0,
            },
        ],
        "model_outputs": {
            "inverter_main": {
                SOURCE_SINK_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            },
            "inverter_main:connection": {
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(5.0,), direction="+"),
                connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(3.0,), direction="-"),
                connection.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            },
        },
        "outputs": {
            inverter_element.INVERTER_DEVICE_INVERTER: {
                inverter_element.INVERTER_DC_BUS_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
                inverter_element.INVERTER_POWER_DC_TO_AC: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(5.0,), direction="+"),
                inverter_element.INVERTER_POWER_AC_TO_DC: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(3.0,), direction="-"),
                inverter_element.INVERTER_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction=None),
                inverter_element.INVERTER_MAX_POWER_DC_TO_AC: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                inverter_element.INVERTER_MAX_POWER_AC_TO_DC: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                inverter_element.INVERTER_MAX_POWER_DC_TO_AC_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                inverter_element.INVERTER_MAX_POWER_AC_TO_DC_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
    {
        "description": "Adapter mapping inverter case without efficiency",
        "element_type": "inverter",
        "schema": inverter_element.InverterConfigSchema(
            element_type="inverter",
            name="inverter_simple",
            connection="network",
            max_power_dc_to_ac=["sensor.max_power"],
            max_power_ac_to_dc=["sensor.max_power"],
        ),
        "data": inverter_element.InverterConfigData(
            element_type="inverter",
            name="inverter_simple",
            connection="network",
            max_power_dc_to_ac=[10.0],
            max_power_ac_to_dc=[10.0],
        ),
        "model": [
            {"element_type": "source_sink", "name": "inverter_simple", "is_source": False, "is_sink": False},
            {
                "element_type": "connection",
                "name": "inverter_simple:connection",
                "source": "inverter_simple",
                "target": "network",
                "max_power_source_target": [10.0],
                "max_power_target_source": [10.0],
                "efficiency_source_target": None,
                "efficiency_target_source": None,
            },
        ],
        "model_outputs": {
            "inverter_simple": {
                SOURCE_SINK_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            },
            "inverter_simple:connection": {
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(5.0,), direction="+"),
                connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(3.0,), direction="-"),
                connection.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            },
        },
        "outputs": {
            inverter_element.INVERTER_DEVICE_INVERTER: {
                inverter_element.INVERTER_DC_BUS_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
                inverter_element.INVERTER_POWER_DC_TO_AC: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(5.0,), direction="+"),
                inverter_element.INVERTER_POWER_AC_TO_DC: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(3.0,), direction="-"),
                inverter_element.INVERTER_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction=None),
                inverter_element.INVERTER_MAX_POWER_DC_TO_AC: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                inverter_element.INVERTER_MAX_POWER_AC_TO_DC: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(10.0,)),
                inverter_element.INVERTER_MAX_POWER_DC_TO_AC_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                inverter_element.INVERTER_MAX_POWER_AC_TO_DC_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
]

# Invalid schema-only cases (deliberately invalid for testing schema validation)
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = [
    {
        "description": "Inverter missing required connection field",
        "schema": inverter_element.InverterConfigSchema(
            element_type="inverter",
            name="inverter_bad",
            connection="",  # Invalid empty connection
            max_power_dc_to_ac=["sensor.max_power"],
            max_power_ac_to_dc=["sensor.max_power"],
        ),
    },
]

# Invalid model parameter combinations to exercise runtime validation
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
