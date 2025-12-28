"""Tests for grid element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import grid as grid_element
from custom_components.haeo.elements.grid import GridConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for create_model_elements."""

    description: str
    data: GridConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Grid with import and export limits",
        "data": GridConfigData(
            element_type="grid",
            name="grid_main",
            connection="network",
            import_price=[0.1],
            export_price=[0.05],
            import_limit=5.0,
            export_limit=3.0,
        ),
        "model": [
            {"element_type": "node", "name": "grid_main", "is_source": True, "is_sink": True},
            {
                "element_type": "connection",
                "name": "grid_main:connection",
                "source": "grid_main",
                "target": "network",
                "max_power_source_target": 5.0,
                "max_power_target_source": 3.0,
                "price_source_target": [0.1],
                "price_target_source": [-0.05],
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Grid with import and export",
        "name": "grid_main",
        "model_outputs": {
            "grid_main:connection": {
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(7.0,), direction="-"
                ),
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(5.0,), direction="+"
                ),
                power_connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(3.0,)
                ),
                power_connection.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(5.0,)
                ),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                power_connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)
                ),
                power_connection.CONNECTION_PRICE_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.1,)
                ),
                power_connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.05,)
                ),
            }
        },
        "outputs": {
            grid_element.GRID_DEVICE_GRID: {
                grid_element.GRID_POWER_EXPORT: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(7.0,), direction="-"
                ),
                grid_element.GRID_POWER_IMPORT: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(5.0,), direction="+"
                ),
                grid_element.GRID_POWER_ACTIVE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(-2.0,), direction=None
                ),
                grid_element.GRID_POWER_MAX_EXPORT: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(3.0,)),
                grid_element.GRID_POWER_MAX_IMPORT: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(5.0,)),
                grid_element.GRID_POWER_MAX_EXPORT_PRICE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                grid_element.GRID_POWER_MAX_IMPORT_PRICE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)
                ),
                grid_element.GRID_PRICE_EXPORT: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.05,)),
                grid_element.GRID_PRICE_IMPORT: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.1,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_create_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["grid"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["grid"]
    result = entry.outputs(case["name"], case["model_outputs"], {})
    assert result == case["outputs"]
