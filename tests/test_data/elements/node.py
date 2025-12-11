"""Test data for node element configuration."""

from collections.abc import Sequence

from custom_components.haeo.elements import node
from custom_components.haeo.model.const import OUTPUT_TYPE_SHADOW_PRICE
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import SOURCE_SINK_POWER_BALANCE

from .types import ElementConfigData, ElementConfigSchema, ElementValidCase, InvalidModelCase, InvalidSchemaCase

# Single fully-typed pipeline case
VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
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
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = [
    {
        "description": "Node missing name",
        "schema": {
            "element_type": "node",
            "name": "",
        },
    },
]

# Invalid model parameter combinations to exercise runtime validation
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
