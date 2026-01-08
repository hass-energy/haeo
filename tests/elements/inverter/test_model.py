"""Tests for inverter element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import inverter as inverter_element
from custom_components.haeo.elements.inverter import InverterConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for create_model_elements."""

    description: str
    data: InverterConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Inverter with efficiency",
        "data": InverterConfigData(
            element_type="inverter",
            name="inverter_main",
            connection="network",
            max_power_dc_to_ac=[10.0],
            max_power_ac_to_dc=[10.0],
            efficiency_dc_to_ac=100.0,
            efficiency_ac_to_dc=100.0,
        ),
        "model": [
            {"element_type": "node", "name": "inverter_main", "is_source": False, "is_sink": False},
            {
                "element_type": "connection",
                "name": "inverter_main:connection",
                "source": "inverter_main",
                "target": "network",
                "max_power_source_target": [10.0],
                "max_power_target_source": [10.0],
                "efficiency_source_target": 100.0,
                "efficiency_target_source": 100.0,
            },
        ],
    },
    {
        "description": "Inverter with default efficiency (100%)",
        "data": InverterConfigData(
            element_type="inverter",
            name="inverter_simple",
            connection="network",
            max_power_dc_to_ac=[10.0],
            max_power_ac_to_dc=[10.0],
            efficiency_dc_to_ac=100.0,
            efficiency_ac_to_dc=100.0,
        ),
        "model": [
            {"element_type": "node", "name": "inverter_simple", "is_source": False, "is_sink": False},
            {
                "element_type": "connection",
                "name": "inverter_simple:connection",
                "source": "inverter_simple",
                "target": "network",
                "max_power_source_target": [10.0],
                "max_power_target_source": [10.0],
                "efficiency_source_target": 100.0,
                "efficiency_target_source": 100.0,
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
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="-"),
                power_connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            },
        },
        "outputs": {
            inverter_element.INVERTER_DEVICE_INVERTER: {
                inverter_element.INVERTER_DC_BUS_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
                inverter_element.INVERTER_POWER_DC_TO_AC: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                inverter_element.INVERTER_POWER_AC_TO_DC: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(3.0,), direction="-"),
                inverter_element.INVERTER_POWER_ACTIVE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction=None),
                inverter_element.INVERTER_MAX_POWER_DC_TO_AC_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                inverter_element.INVERTER_MAX_POWER_AC_TO_DC_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_create_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["inverter"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["inverter"]
    result = entry.outputs(case["name"], case["model_outputs"], {})
    assert result == case["outputs"]
