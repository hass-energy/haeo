"""Tests for connection element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import connection as connection_element
from custom_components.haeo.elements.connection import ConnectionConfigData
from custom_components.haeo.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements import connection as model_connection
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema import as_connection_target
from tests.util.normalize import normalize_for_compare


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
            element_type="connection",
            common={"name": "c1"},
            endpoints={"source": as_connection_target("s"), "target": as_connection_target("t")},
            power_limits={
                "max_power_source_target": np.array([4.0]),
                "max_power_target_source": np.array([2.0]),
            },
            pricing={
                "price_source_target": np.array([0.1]),
                "price_target_source": np.array([0.05]),
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.90]),
            },
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "c1",
                "source": "s",
                "target": "t",
                "mirror_segment_order": False,
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": [0.95],
                        "efficiency_target_source": [0.90],
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [4.0],
                        "max_power_target_source": [2.0],
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": [0.1],
                        "price_target_source": [0.05],
                    },
                },
            }
        ],
    },
    {
        "description": "Connection without optional fields",
        "data": ConnectionConfigData(
            element_type="connection",
            common={"name": "c_min"},
            endpoints={"source": as_connection_target("s"), "target": as_connection_target("t")},
            power_limits={},
            pricing={},
            efficiency={},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "c_min",
                "source": "s",
                "target": "t",
                "mirror_segment_order": False,
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": None,
                        "efficiency_target_source": None,
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": None,
                        "max_power_target_source": None,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": None,
                        "price_target_source": None,
                    },
                },
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
                model_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                model_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                model_connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "source_target": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                        "target_source": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                        "time_slice": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.001,)),
                    }
                },
            }
        },
        "outputs": {
            connection_element.CONNECTION_DEVICE_CONNECTION: {
                connection_element.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection_element.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                connection_element.CONNECTION_POWER_ACTIVE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(-2.0,), direction=None),
                connection_element.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                connection_element.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                connection_element.CONNECTION_TIME_SLICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.001,)),
            }
        },
    },
    {
        "description": "Connection without optional fields",
        "name": "c_min",
        "model_outputs": {
            "c_min": {
                model_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                model_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
            }
        },
        "outputs": {
            connection_element.CONNECTION_DEVICE_CONNECTION: {
                connection_element.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                connection_element.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(7.0,), direction="-"),
                connection_element.CONNECTION_POWER_ACTIVE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(-2.0,), direction=None),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["connection"]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["connection"]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
