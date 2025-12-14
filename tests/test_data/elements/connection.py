"""Test data for connection element configuration."""

from collections.abc import Sequence
from custom_components.haeo.elements import connection as connection_element
from custom_components.haeo.model import connection as connection_model
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData

from .types import ElementConfigData, ElementConfigSchema, ElementValidCase, InvalidModelCase, InvalidSchemaCase

# Single fully-typed pipeline case
VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
    {
        "description": "Adapter mapping connection case",
        "element_type": "connection",
        "schema": connection_element.ConnectionConfigSchema(
            element_type="connection",
            name="c1",
            source="s",
            target="t",
            max_power_source_target=["sensor.connection_max_power_st"],
            max_power_target_source=["sensor.connection_max_power_ts"],
            efficiency_source_target="sensor.connection_eff_st",
            efficiency_target_source="sensor.connection_eff_ts",
            price_source_target=["sensor.connection_price_st"],
            price_target_source=["sensor.connection_price_ts"],
        ),
        "data": connection_element.ConnectionConfigData(
            element_type="connection",
            name="c1",
            source="s",
            target="t",
            max_power_source_target=[4.0],
            max_power_target_source=[2.0],
            efficiency_source_target=[95.0],
            efficiency_target_source=[90.0],
            price_source_target=[0.1],
            price_target_source=[0.05],
        ),
        "model": [
            {
                "element_type": "connection",
                "name": "c1",
                "source": "s",
                "target": "t",
                "max_power_source_target": [4.0],
                "max_power_target_source": [2.0],
                "efficiency_source_target": [95.0],
                "efficiency_target_source": [90.0],
                "price_source_target": [0.1],
                "price_target_source": [0.05],
            }
        ],
        "model_outputs": {
            "c1": {
                connection_model.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection_model.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                connection_model.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(4.0,)),
                connection_model.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                connection_model.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection_model.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                connection_model.CONNECTION_PRICE_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.1,)),
                connection_model.CONNECTION_PRICE_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.05,)),
                connection_model.CONNECTION_TIME_SLICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.001,)),
            }
        },
        "outputs": {
            connection_element.CONNECTION_DEVICE_CONNECTION: {
                connection_element.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection_element.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                connection_element.CONNECTION_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(-2.0,), direction=None),
                connection_element.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(4.0,)),
                connection_element.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                connection_element.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection_element.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                connection_element.CONNECTION_PRICE_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.1,)),
                connection_element.CONNECTION_PRICE_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.05,)),
                connection_element.CONNECTION_TIME_SLICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.001,)),
            }
        },
    },
    {
        "description": "Adapter mapping connection without optional limits or prices",
        "element_type": "connection",
        "schema": connection_element.ConnectionConfigSchema(
            element_type="connection",
            name="c_min",
            source="s",
            target="t",
        ),
        "data": connection_element.ConnectionConfigData(
            element_type="connection",
            name="c_min",
            source="s",
            target="t",
        ),
        "model": [
            {
                "element_type": "connection",
                "name": "c_min",
                "source": "s",
                "target": "t",
                "max_power_source_target": None,
                "max_power_target_source": None,
                "efficiency_source_target": None,
                "efficiency_target_source": None,
                "price_source_target": None,
                "price_target_source": None,
            }
        ],
        "model_outputs": {
            "c_min": {
                connection_model.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection_model.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
            }
        },
        "outputs": {
            connection_element.CONNECTION_DEVICE_CONNECTION: {
                connection_element.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection_element.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                connection_element.CONNECTION_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(-2.0,), direction=None),
            }
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = [
    {
        "description": "Connection has empty endpoints",
        "schema": {
            "element_type": "connection",
            "name": "Missing Source",
            "source": "",
            "target": "",
            "max_power_source_target": ["sensor.bad_max_power"],
        },
    },
]

# Invalid model parameter combinations to exercise runtime validation
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
