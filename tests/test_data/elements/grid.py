"""Test data for grid element configuration."""

from collections.abc import Sequence
from custom_components.haeo.elements import grid as grid_element
from custom_components.haeo.model import connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData

from .types import ElementConfigData, ElementConfigSchema, ElementValidCase, InvalidModelCase, InvalidSchemaCase

# Single fully-typed pipeline case
VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
    {
        "description": "Adapter mapping grid case",
        "element_type": "grid",
        "schema": grid_element.GridConfigSchema(
            element_type="grid",
            name="grid_main",
            connection="network",
            import_price=["sensor.grid_import_price"],
            export_price=["sensor.grid_export_price"],
            import_limit=5.0,
            export_limit=3.0,
        ),
        "data": grid_element.GridConfigData(
            element_type="grid",
            name="grid_main",
            connection="network",
            import_price=[0.1],
            export_price=[0.05],
            import_limit=5.0,
            export_limit=3.0,
        ),
        "model": [
            {"element_type": "source_sink", "name": "grid_main", "is_source": True, "is_sink": True},
            {
                "element_type": "connection",
                "name": "grid_main:connection",
                "source": "grid_main",
                "target": "network",
                "max_power_source_target": 5.0,
                "max_power_target_source": 3.0,
                "price_source_target": [0.1],
                "price_target_source": [-0.05],
            },
        ],
        "model_outputs": {
            "grid_main:connection": {
                connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
        "outputs": {
            grid_element.GRID_DEVICE_GRID: {
                grid_element.GRID_POWER_EXPORT: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(7.0,), direction="-"),
                grid_element.GRID_POWER_IMPORT: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(5.0,), direction="+"),
                grid_element.GRID_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(-2.0,), direction=None),
                grid_element.GRID_POWER_MAX_EXPORT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                grid_element.GRID_POWER_MAX_IMPORT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = [
    {
        "description": "Grid negative import limit",
        "schema": {
            "element_type": "grid",
            "name": "grid_bad",
            "connection": "network",
            "import_price": ["sensor.import_price"],
            "export_price": ["sensor.export_price"],
            "import_limit": -1.0,
        },
    },
]

# Invalid model parameter combinations to exercise runtime validation
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
