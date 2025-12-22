"""Test data for load element configuration."""

from collections.abc import Sequence
from custom_components.haeo.elements import load as load_element
from custom_components.haeo.model import connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import FORECAST_SOURCE_CUSTOM_SENSOR, FORECAST_SOURCE_ENERGY_TAB

from .types import ElementConfigData, ElementConfigSchema, ElementValidCase, InvalidModelCase, InvalidSchemaCase

VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
    {
        "description": "Load with custom sensor forecast source",
        "element_type": "load",
        "schema": load_element.LoadConfigSchema(
            element_type="load",
            name="load_main",
            connection="network",
            forecast_source=FORECAST_SOURCE_CUSTOM_SENSOR,
            forecast=["sensor.load_forecast_1", "sensor.load_forecast_2"],
        ),
        "data": load_element.LoadConfigData(
            element_type="load",
            name="load_main",
            connection="network",
            forecast_source=FORECAST_SOURCE_CUSTOM_SENSOR,
            forecast=[1.0, 2.0],
        ),
        "model": [
            {"element_type": "source_sink", "name": "load_main", "is_source": False, "is_sink": True},
            {
                "element_type": "connection",
                "name": "load_main:connection",
                "source": "load_main",
                "target": "network",
                "max_power_source_target": 0.0,
                "max_power_target_source": [1.0, 2.0],
                "fixed_power": True,
            },
        ],
        "model_outputs": {
            "load_main:connection": {
                connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="+"),
                connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
        "outputs": {
            load_element.LOAD_DEVICE_LOAD: {
                load_element.LOAD_POWER: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="+"),
                load_element.LOAD_POWER_POSSIBLE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                load_element.LOAD_FORECAST_LIMIT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
    },
    {
        "description": "Load with energy tab forecast source",
        "element_type": "load",
        "schema": load_element.LoadConfigSchema(
            element_type="load",
            name="load_energy_tab",
            connection="network",
            forecast_source=FORECAST_SOURCE_ENERGY_TAB,
            history_days=7,
        ),
        "data": load_element.LoadConfigData(
            element_type="load",
            name="load_energy_tab",
            connection="network",
            forecast_source=FORECAST_SOURCE_ENERGY_TAB,
            history_days=[1.5, 2.0, 1.8],  # Loaded power values from historical data
        ),
        "model": [
            {"element_type": "source_sink", "name": "load_energy_tab", "is_source": False, "is_sink": True},
            {
                "element_type": "connection",
                "name": "load_energy_tab:connection",
                "source": "load_energy_tab",
                "target": "network",
                "max_power_source_target": 0.0,
                "max_power_target_source": [1.5, 2.0, 1.8],
                "fixed_power": True,
            },
        ],
        "model_outputs": {
            "load_energy_tab:connection": {
                connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.5,), direction="+"),
                connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
        "outputs": {
            load_element.LOAD_DEVICE_LOAD: {
                load_element.LOAD_POWER: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.5,), direction="+"),
                load_element.LOAD_POWER_POSSIBLE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                load_element.LOAD_FORECAST_LIMIT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = [
    {
        "description": "Load missing connection",
        "schema": {
            "element_type": "load",
            "name": "load_bad",
            "connection": "",
            "forecast_source": FORECAST_SOURCE_CUSTOM_SENSOR,
            "forecast": ["sensor.load1", "sensor.load2"],
        },
    },
    {
        "description": "Load with invalid forecast source",
        "schema": {
            "element_type": "load",
            "name": "load_bad_source",
            "connection": "network",
            "forecast_source": "invalid_source",
            "forecast": ["sensor.load1"],
        },
    },
]

# Invalid model parameter combinations to exercise runtime validation
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
