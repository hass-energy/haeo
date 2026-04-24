"""Tests for load element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.load import LOAD_DEVICE_LOAD, LOAD_FORECAST_LIMIT_PRICE, LOAD_POWER
from custom_components.haeo.core.adapters.elements.tests.normalize import normalize_for_compare
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    connection,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.load import LoadConfigData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: LoadConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    config: LoadConfigData
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Load with forecast",
        "data": LoadConfigData(
            element_type=ElementType.LOAD,
            name="load_main",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.0, 2.0])},
            curtailment={},
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "load_main", "is_source": False, "is_sink": True},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "load_main:connection",
                "source": "network",
                "target": "load_main",
                "is_time_sensitive": True,
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [1.0, 2.0], "fixed": True},
                },
            },
        ],
    },
    {
        "description": "Sheddable load",
        "data": LoadConfigData(
            element_type=ElementType.LOAD,
            name="load_sheddable",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.0, 2.0])},
            curtailment={"curtailment": True},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": "load_sheddable",
                "is_source": False,
                "is_sink": True,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "load_sheddable:connection",
                "source": "network",
                "target": "load_sheddable",
                "is_time_sensitive": True,
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [1.0, 2.0], "fixed": False},
                },
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Load with forecast",
        "name": "load_main",
        "config": LoadConfigData(
            element_type=ElementType.LOAD,
            name="load_main",
            connection=as_connection_target("network"),
            forecast={"forecast": np.array([1.0, 2.0])},
            curtailment={},
        ),
        "model_outputs": {
            "load_main:connection": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,))
                    }
                },
            }
        },
        "outputs": {
            LOAD_DEVICE_LOAD: {
                LOAD_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-", fixed=True),
                LOAD_FORECAST_LIMIT_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES[ElementType.LOAD]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES[ElementType.LOAD]
    result = entry.outputs(case["name"], case["model_outputs"], config=case["config"])
    assert result == case["outputs"]
