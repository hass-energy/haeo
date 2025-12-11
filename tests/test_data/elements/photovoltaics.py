"""Test data for photovoltaics element configuration."""

from collections.abc import Sequence

from custom_components.haeo.elements import photovoltaics
from custom_components.haeo.model import connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData

from .types import ElementConfigData, ElementConfigSchema, ElementValidCase, InvalidModelCase, InvalidSchemaCase

VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
    {
        "description": "Adapter mapping photovoltaics case",
        "element_type": "photovoltaics",
        "schema": photovoltaics.PhotovoltaicsConfigSchema(
            element_type="photovoltaics",
            name="pv_main",
            connection="network",
            forecast=["sensor.pv_forecast_1", "sensor.pv_forecast_2"],
            price_production=0.15,
            curtailment=False,
        ),
        "data": photovoltaics.PhotovoltaicsConfigData(
            element_type="photovoltaics",
            name="pv_main",
            connection="network",
            forecast=[2.0, 1.5],
            price_production=0.15,
            curtailment=False,
        ),
        "model": [
            {"element_type": "source_sink", "name": "pv_main", "is_source": True, "is_sink": False},
            {
                "element_type": "connection",
                "name": "pv_main:connection",
                "source": "pv_main",
                "target": "network",
                "max_power_source_target": [2.0, 1.5],
                "max_power_target_source": 0.0,
                "fixed_power": True,
                "price_source_target": 0.15,
            },
        ],
        "model_outputs": {
            "pv_main:connection": {
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(2.0,), direction="+"),
                connection.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
        "outputs": {
            "pv_main": {
                photovoltaics.PHOTOVOLTAICS_POWER: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction="+"),
                photovoltaics.PHOTOVOLTAICS_POWER_AVAILABLE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                photovoltaics.PHOTOVOLTAICS_FORECAST_LIMIT: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = [
    {
        "description": "Photovoltaics missing connection",
        "schema": {
            "element_type": "photovoltaics",
            "name": "pv_bad",
            "connection": "",
            "forecast": ["sensor.pv1", "sensor.pv2"],
        },
    },
]

# Invalid model parameter combinations to exercise runtime validation
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
