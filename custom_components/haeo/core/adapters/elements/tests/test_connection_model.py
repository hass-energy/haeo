"""Tests for connection element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.connection import (
    CONNECTION_DEVICE_CONNECTION,
    CONNECTION_POWER,
    CONNECTION_POWER_ACTIVE,
)
from custom_components.haeo.core.adapters.elements.tests.normalize import normalize_for_compare
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
)
from custom_components.haeo.core.model.elements import connection as model_connection
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: ConnectionConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Connection with all optional fields",
        "data": ConnectionConfigData(
            element_type=ElementType.CONNECTION,
            name="conn",
            endpoints={"source": as_connection_target("s"), "target": as_connection_target("t")},
            power_limits={
                "max_power_source_target": np.array([4.0]),
                "max_power_target_source": np.array([2.0]),
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.90]),
            },
            pricing={
                "price_source_target": np.array([0.1]),
                "price_target_source": np.array([0.05]),
            },
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn:forward",
                "source": "s",
                "target": "t",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                    "power_limit": {"segment_type": "power_limit", "max_power": [4.0]},
                    "pricing": {"segment_type": "pricing", "price": [0.1]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn:reverse",
                "source": "t",
                "target": "s",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.90]},
                    "power_limit": {"segment_type": "power_limit", "max_power": [2.0]},
                    "pricing": {"segment_type": "pricing", "price": [0.05]},
                },
            },
        ],
    },
    {
        "description": "Connection with minimal fields",
        "data": ConnectionConfigData(
            element_type=ElementType.CONNECTION,
            name="conn_min",
            endpoints={"source": as_connection_target("s"), "target": as_connection_target("t")},
            power_limits={},
            efficiency={},
            pricing={},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn_min:forward",
                "source": "s",
                "target": "t",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": None},
                    "power_limit": {"segment_type": "power_limit", "max_power": None},
                    "pricing": {"segment_type": "pricing", "price": None},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "conn_min:reverse",
                "source": "t",
                "target": "s",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": None},
                    "power_limit": {"segment_type": "power_limit", "max_power": None},
                    "pricing": {"segment_type": "pricing", "price": None},
                },
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Connection with all optional fields",
        "name": "c1",
        "model_outputs": {
            "c1:forward": {
                model_connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
            },
            "c1:reverse": {
                model_connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(7.0,), direction="-"
                ),
            },
        },
        "outputs": {
            CONNECTION_DEVICE_CONNECTION: {
                CONNECTION_POWER: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                CONNECTION_POWER_ACTIVE: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(-2.0,), direction=None
                ),
            }
        },
    },
    {
        "description": "Connection without optional fields",
        "name": "c_min",
        "model_outputs": {
            "c_min:forward": {
                model_connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
            },
            "c_min:reverse": {
                model_connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(7.0,), direction="-"
                ),
            },
        },
        "outputs": {
            CONNECTION_DEVICE_CONNECTION: {
                CONNECTION_POWER: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                CONNECTION_POWER_ACTIVE: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(-2.0,), direction=None
                ),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES[ElementType.CONNECTION]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES[ElementType.CONNECTION]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
