"""Tests for inverter element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.adapters.elements.inverter import (
    INVERTER_DC_BUS_POWER_BALANCE_SHADOW_ENERGY_PRICE,
    INVERTER_DEVICE_INVERTER,
    INVERTER_MAX_POWER_AC_TO_DC_SHADOW_ENERGY_PRICE,
    INVERTER_MAX_POWER_DC_TO_AC_SHADOW_ENERGY_PRICE,
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
    periods: NDArray[np.floating[Any]]
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
                "max_power_target_source": np.array([8.0]),
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
                "name": "inverter_main:dc_to_ac",
                "source": "inverter_main",
                "target": "network",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                    "power_limit": {"segment_type": "power_limit", "max_power": [10.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_main:ac_to_dc",
                "source": "network",
                "target": "inverter_main",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                    "power_limit": {"segment_type": "power_limit", "max_power": [8.0]},
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
                "name": "inverter_simple:dc_to_ac",
                "source": "inverter_simple",
                "target": "network",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                    "power_limit": {"segment_type": "power_limit", "max_power": [10.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "inverter_simple:ac_to_dc",
                "source": "network",
                "target": "inverter_simple",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": 1.0},
                    "power_limit": {"segment_type": "power_limit", "max_power": [10.0]},
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
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "inverter_main:dc_to_ac": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.02,)),
                    }
                },
            },
            "inverter_main:ac_to_dc": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="-"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "power_limit": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.04,)),
                    }
                },
            },
        },
        "periods": np.array([0.5]),
        "outputs": {
            INVERTER_DEVICE_INVERTER: {
                INVERTER_DC_BUS_POWER_BALANCE_SHADOW_ENERGY_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                INVERTER_POWER_DC_TO_AC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                INVERTER_POWER_AC_TO_DC: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="-"
                ),
                INVERTER_POWER_ACTIVE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction=None),
                INVERTER_MAX_POWER_DC_TO_AC_SHADOW_ENERGY_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.02,)
                ),
                INVERTER_MAX_POWER_AC_TO_DC_SHADOW_ENERGY_PRICE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.04,)
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
    result = entry.outputs(case["name"], case["model_outputs"], periods=case["periods"])

    expected = case["outputs"]
    assert result.keys() == expected.keys()
    for device_name, device_outputs in expected.items():
        assert result[device_name].keys() == device_outputs.keys()
        for output_name, expected_output in device_outputs.items():
            actual = result[device_name][output_name]
            assert actual.type == expected_output.type
            assert actual.unit == expected_output.unit
            assert actual.direction == expected_output.direction
            assert len(actual.values) == len(expected_output.values)
            for a, e in zip(actual.values, expected_output.values, strict=True):
                assert a == pytest.approx(e)
