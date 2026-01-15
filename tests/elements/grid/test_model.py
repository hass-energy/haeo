"""Tests for grid element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import grid as grid_element
from custom_components.haeo.elements.grid import GridConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements import power_connection
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: GridConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    config: GridConfigData
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    periods: list[float]
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
            import_limit=[5.0],
            export_limit=[3.0],
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid_main", "is_source": True, "is_sink": True},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "grid_main:connection",
                "source": "grid_main",
                "target": "network",
                "max_power_source_target": [5.0],
                "max_power_target_source": [3.0],
                "price_source_target": [0.1],
                "price_target_source": [-0.05],
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Grid with import and export - cost/revenue calculated from power × price × period",
        "name": "grid_main",
        "config": GridConfigData(element_type="grid", name="grid_main", connection="network", import_price=[0.10], export_price=[0.05]),
        "model_outputs": {
            "grid_main:connection": {
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction="-"),
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="+"),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                power_connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
        "periods": [1.0],  # 1 hour period
        # Cost/revenue calculations:
        # import_cost = 5.0 kW × $0.10/kWh × 1h = $0.50
        # export_revenue = 2.0 kW × $0.05/kWh × 1h = $0.10 (positive!)
        # net_cost = $0.50 - $0.10 = $0.40
        # Cumulative values in chronological order
        "outputs": {
            grid_element.GRID_DEVICE_GRID: {
                grid_element.GRID_POWER_EXPORT: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"),
                grid_element.GRID_POWER_IMPORT: OutputData(type=OutputType.POWER, unit="kW", values=(5.0,), direction="+"),
                grid_element.GRID_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(3.0,), direction=None),
                grid_element.GRID_COST_IMPORT: OutputData(type=OutputType.COST, unit="$", values=(0.50,), direction="-", state_last=True),
                grid_element.GRID_REVENUE_EXPORT: OutputData(type=OutputType.COST, unit="$", values=(0.10,), direction="+", state_last=True),
                grid_element.GRID_COST_NET: OutputData(type=OutputType.COST, unit="$", values=(0.40,), direction=None, state_last=True),
                grid_element.GRID_POWER_MAX_EXPORT_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                grid_element.GRID_POWER_MAX_IMPORT_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
    {
        "description": "Grid with multiple periods - cumulative cost/revenue",
        "name": "grid_multi",
        "config": GridConfigData(element_type="grid", name="grid_multi", connection="network", import_price=[0.10, 0.20], export_price=[0.05, 0.05]),
        "model_outputs": {
            "grid_multi:connection": {
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.0, 0.0), direction="-"),
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0, 3.0), direction="+"),
            }
        },
        "periods": [0.5, 0.5],  # 30 min periods
        # Cost/revenue calculations (per period, then cumulative):
        # Period 1: import_cost = 5.0 kW × $0.10/kWh × 0.5h = $0.25
        # Period 2: import_cost = 3.0 kW × $0.20/kWh × 0.5h = $0.30
        # Cumulative: [$0.25, $0.55]
        "outputs": {
            grid_element.GRID_DEVICE_GRID: {
                grid_element.GRID_POWER_EXPORT: OutputData(type=OutputType.POWER, unit="kW", values=(0.0, 0.0), direction="-"),
                grid_element.GRID_POWER_IMPORT: OutputData(type=OutputType.POWER, unit="kW", values=(5.0, 3.0), direction="+"),
                grid_element.GRID_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(5.0, 3.0), direction=None),
                grid_element.GRID_COST_IMPORT: OutputData(type=OutputType.COST, unit="$", values=(0.25, 0.55), direction="-", state_last=True),
                grid_element.GRID_REVENUE_EXPORT: OutputData(type=OutputType.COST, unit="$", values=(0.0, 0.0), direction="+", state_last=True),
                grid_element.GRID_COST_NET: OutputData(type=OutputType.COST, unit="$", values=(0.25, 0.55), direction=None, state_last=True),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["grid"]
    result = entry.model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs with cost calculation."""
    entry = ELEMENT_TYPES["grid"]
    result = entry.outputs(case["name"], case["model_outputs"], config=case["config"], periods=case["periods"])
    assert result == case["outputs"]
