"""Tests for inverter element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.inverter import (
    INVERTER_DC_BUS_POWER_BALANCE,
    INVERTER_DEVICE_INVERTER,
    INVERTER_MAX_POWER_AC_TO_DC_PRICE,
    INVERTER_MAX_POWER_DC_TO_AC_PRICE,
    INVERTER_POWER_AC_TO_DC,
    INVERTER_POWER_ACTIVE,
    INVERTER_POWER_DC_TO_AC,
)
from custom_components.haeo.core.adapters.elements.tests.normalize import normalize_for_compare
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    connection,
)
from custom_components.haeo.core.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.inverter import InverterConfigData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: InverterConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Inverter with efficiency",
        "data": InverterConfigData(
            element_type=ElementType.INVERTER,
            name="inverter_main",
            connection=as_connection_target("network"),
            power_limits={
                "max_power_source_target": np.array([10.0]),
                "max_power_target_source": np.array([10.0]),
            },
            efficiency={
                "efficiency_source_target": np.array(1.0),
                "efficiency_target_source": np.array(1.0),
            },
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "inverter_main", "is_source": False, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_main:connection",
                "source": "inverter_main",
                "target": "network",
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": 1.0,
                        "efficiency_target_source": 1.0,
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [10.0],
                        "max_power_target_source": [10.0],
                    },
                },
            },
        ],
    },
    {
        "description": "Inverter with default efficiency (100%)",
        "data": InverterConfigData(
            element_type=ElementType.INVERTER,
            name="inverter_simple",
            connection=as_connection_target("network"),
            power_limits={
                "max_power_source_target": np.array([10.0]),
                "max_power_target_source": np.array([10.0]),
            },
            efficiency={
                "efficiency_source_target": np.array(1.0),
                "efficiency_target_source": np.array(1.0),
            },
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "inverter_simple", "is_source": False, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_simple:connection",
                "source": "inverter_simple",
                "target": "network",
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": 1.0,
                        "efficiency_target_source": 1.0,
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [10.0],
                        "max_power_target_source": [10.0],
                    },
                },
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Inverter with all outputs",
        "name": "inverter_main",
        "model_outputs": {
            "inverter_main": {
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            },
            "inverter_main:connection": {
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="-"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "source_target": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                        "target_source": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                    }
                },
            },
        },
        "outputs": {
            INVERTER_DEVICE_INVERTER: {
                INVERTER_DC_BUS_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
                INVERTER_POWER_DC_TO_AC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                INVERTER_POWER_AC_TO_DC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="-"
                ),
                INVERTER_POWER_ACTIVE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction=None),
                INVERTER_MAX_POWER_DC_TO_AC_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                INVERTER_MAX_POWER_AC_TO_DC_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)
                ),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES[ElementType.INVERTER]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES[ElementType.INVERTER]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
