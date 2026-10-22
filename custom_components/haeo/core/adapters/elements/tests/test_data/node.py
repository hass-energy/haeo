"""Adapter mapping cases for the node element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.node import NODE_DEVICE_NODE, NODE_POWER_BALANCE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.node import NodeConfigData

from . import CreateCase, OutputsCase

PASSTHROUGH = NodeConfigData(
    element_type=ElementType.NODE,
    name="node_main",
    role={"is_source": False, "is_sink": False},
)

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Node as passthrough",
        "data": PASSTHROUGH,
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "node_main", "is_source": False, "is_sink": False},
        ],
    },
    {
        "description": "Node with an empty role section neither sources nor sinks",
        "data": NodeConfigData(element_type=ElementType.NODE, name="node_default", role={}),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "node_default", "is_source": False, "is_sink": False},
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Node with power balance",
        "data": PASSTHROUGH,
        "model_outputs": {
            "node_main": {
                ELEMENT_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            }
        },
        "periods": np.array([1.0]),
        "outputs": {
            NODE_DEVICE_NODE: {
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            }
        },
    },
    {
        "description": "Unconstrained node without power balance",
        "data": PASSTHROUGH,
        "model_outputs": {"node_main": {}},
        "periods": np.array([1.0]),
        "outputs": {NODE_DEVICE_NODE: {}},
    },
]
