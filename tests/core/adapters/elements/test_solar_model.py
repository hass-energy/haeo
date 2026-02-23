"""Tests for solar element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.solar import SOLAR_DEVICE_SOLAR, SOLAR_FORECAST_LIMIT, SOLAR_POWER
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
from custom_components.haeo.core.schema.elements.solar import SolarConfigData
from tests.util.normalize import normalize_for_compare


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: SolarConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Solar with production price",
        "data": SolarConfigData(
            element_type=ElementType.SOLAR,
            name="pv_main",
            connection=as_connection_target("network"),
            forecast={
                "forecast": np.array([2.0, 1.5]),
            },
            pricing={
                "price_source_target": np.array([0.15, 0.15]),
            },
            curtailment={
                "curtailment": False,
            },
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "pv_main", "is_source": True, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "pv_main:connection",
                "source": "pv_main",
                "target": "network",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [2.0, 1.5],
                        "max_power_target_source": 0.0,
                        "fixed": True,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": [0.15, 0.15],
                        "price_target_source": None,
                    },
                },
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Solar with forecast limit",
        "name": "pv_main",
        "model_outputs": {
            "pv_main:connection": {
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "source_target": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,))
                    }
                },
            }
        },
        "outputs": {
            SOLAR_DEVICE_SOLAR: {
                SOLAR_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="+"),
                SOLAR_FORECAST_LIMIT: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
    {
        "description": "Solar with shadow price output",
        "name": "pv_with_price",
        "model_outputs": {
            "pv_with_price:connection": {
                connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(1.5,), direction="+"
                ),
                connection.CONNECTION_SEGMENTS: {
                    "power_limit": {
                        "source_target": OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,))
                    }
                },
            }
        },
        "outputs": {
            SOLAR_DEVICE_SOLAR: {
                SOLAR_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(1.5,), direction="+"),
                SOLAR_FORECAST_LIMIT: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES[ElementType.SOLAR]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES[ElementType.SOLAR]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
