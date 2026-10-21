"""Adapter mapping cases for the junction element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.junction import JUNCTION_DEVICE_JUNCTION, JUNCTION_POWER_BALANCE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.junction import JunctionConfigData

from . import CreateCase, OutputsCase

SWITCHBOARD = JunctionConfigData(element_type=ElementType.JUNCTION, name="Switchboard")

BALANCE = OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.1, 0.2))

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Junction is a model node that neither produces nor consumes power",
        "data": SWITCHBOARD,
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "Switchboard", "is_source": False, "is_sink": False}
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Node power balance becomes the junction power balance",
        "data": SWITCHBOARD,
        "model_outputs": {"Switchboard": {ELEMENT_POWER_BALANCE: BALANCE}},
        "periods": np.array([1.0, 1.0]),
        "outputs": {JUNCTION_DEVICE_JUNCTION: {JUNCTION_POWER_BALANCE: BALANCE}},
    },
    {
        "description": "Junction without a power balance has no outputs",
        "data": SWITCHBOARD,
        "model_outputs": {"Switchboard": {}},
        "periods": np.array([1.0, 1.0]),
        "outputs": {JUNCTION_DEVICE_JUNCTION: {}},
    },
]
