"""Test data for grid element configuration."""

from typing import Any

from custom_components.haeo.elements import grid
from custom_components.haeo.model import connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData

from .types import ElementValidCase

# Single fully-typed pipeline case
VALID: list[ElementValidCase[grid.GridConfigSchema, grid.GridConfigData]] = [
    {
        "description": "Adapter mapping grid case",
        "element_type": "grid",
        "schema": grid.GridConfigSchema(
            element_type="grid",
            name="grid_main",
            connection="network",
            import_price=["sensor.grid_import_price"],
            export_price=["sensor.grid_export_price"],
            import_limit=5.0,
            export_limit=3.0,
        ),
        "data": grid.GridConfigData(
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
                connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.4,), direction="-"),
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.3,), direction="+"),
                connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(3.0,)),
                connection.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(5.0,)),
                connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                connection.CONNECTION_PRICE_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.1,)),
                connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.05,)),
            }
        },
        "outputs": {
            "grid_main": {
                grid.GRID_POWER_EXPORT: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.4,), direction="-"),
                grid.GRID_POWER_IMPORT: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.3,), direction="+"),
                grid.GRID_POWER_MAX_EXPORT: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(3.0,)),
                grid.GRID_POWER_MAX_IMPORT: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(5.0,)),
                grid.GRID_POWER_MAX_EXPORT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                grid.GRID_POWER_MAX_IMPORT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                grid.GRID_PRICE_EXPORT: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.05,)),
                grid.GRID_PRICE_IMPORT: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.1,)),
            }
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: list[dict[str, Any]] = [
    {
        "description": "Grid missing connection",
        "schema": {
            "element_type": "grid",
            "name": "grid_bad",
            "import_price": [0.1],
            "export_price": [0.05],
        },
    },
]
