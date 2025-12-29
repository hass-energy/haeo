"""Tests for connection element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import connection as connection_element
from custom_components.haeo.elements.connection import ConnectionConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for create_model_elements."""

    description: str
    data: ConnectionConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Connection with all optional fields",
        "data": ConnectionConfigData(
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
    },
    {
        "description": "Connection without optional fields",
        "data": ConnectionConfigData(
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
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Connection with all optional fields",
        "name": "c1",
        "model_outputs": {
            "c1": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                power_connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                power_connection.CONNECTION_TIME_SLICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.001,)),
            }
        },
        "outputs": {
            connection_element.CONNECTION_DEVICE_CONNECTION: {
                connection_element.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection_element.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                connection_element.CONNECTION_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(-2.0,), direction=None),
                connection_element.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection_element.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                connection_element.CONNECTION_TIME_SLICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.001,)),
            }
        },
    },
    {
        "description": "Connection without optional fields",
        "name": "c_min",
        "model_outputs": {
            "c_min": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
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


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_create_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["connection"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["connection"]
    result = entry.outputs(case["name"], case["model_outputs"], {})
    assert result == case["outputs"]
