"""Test data for node element configuration."""

from typing import Any

from custom_components.haeo.elements import node
from custom_components.haeo.model.const import OUTPUT_TYPE_SHADOW_PRICE
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import SOURCE_SINK_POWER_BALANCE

from .types import ElementValidCase

# Single fully-typed pipeline case
VALID: list[ElementValidCase[node.NodeConfigSchema, node.NodeConfigData]] = [
    {
        "description": "Adapter mapping node case",
        "element_type": "node",
        "schema": node.NodeConfigSchema(element_type="node", name="node_main"),
        "data": node.NodeConfigData(element_type="node", name="node_main"),
        "model": [
            {"element_type": "source_sink", "name": "node_main", "is_source": False, "is_sink": False},
        ],
        "model_outputs": {
            "node_main": {
                SOURCE_SINK_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
        "outputs": {
            "node_main": {
                node.NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: list[dict[str, Any]] = [
    {
        "description": "Node missing name",
        "schema": {
            "element_type": "node",
        },
    },
]
