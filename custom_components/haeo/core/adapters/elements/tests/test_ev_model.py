"""Tests for EV element adapter model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.adapters.elements.ev import (
    EV_DEVICE_EV,
    EV_ENERGY_STORED,
    EV_POWER_ACTIVE,
    EV_POWER_BALANCE,
    EV_POWER_CHARGE,
    EV_POWER_DISCHARGE,
    EV_POWER_MAX_CHARGE_PRICE,
    EV_POWER_MAX_DISCHARGE_PRICE,
    EV_PUBLIC_CHARGE_POWER,
    EV_STATE_OF_CHARGE,
    EV_TRIP_ENERGY_REQUIRED,
)
from custom_components.haeo.core.adapters.elements.tests.normalize import normalize_for_compare
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model import battery as model_battery
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
)
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER_SOURCE_TARGET, CONNECTION_SEGMENTS
from custom_components.haeo.core.model.elements.segments import POWER_LIMIT_SOURCE_TARGET, POWER_LIMIT_TARGET_SOURCE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import EvConfigData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: EvConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    config: EvConfigData
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    periods: NDArray[np.floating[Any]]
    outputs: Mapping[str, Mapping[str, OutputData]]


def _make_ev_config(
    *,
    name: str = "my_ev",
    capacity: float = 60.0,
    energy_per_distance: float = 0.2,
    current_soc: float = 80.0,
    max_charge_rate: float | None = 7.4,
    max_discharge_rate: float | None = None,
    public_charging_price: float | None = None,
    max_power_st: float | None = None,
    max_power_ts: float | None = None,
    efficiency_st: float | None = None,
    efficiency_ts: float | None = None,
) -> EvConfigData:
    """Construct EvConfigData for tests."""
    charging: dict[str, Any] = {}
    if max_charge_rate is not None:
        charging["max_charge_rate"] = np.array([max_charge_rate])
    if max_discharge_rate is not None:
        charging["max_discharge_rate"] = np.array([max_discharge_rate])

    power_limits: dict[str, Any] = {}
    if max_power_st is not None:
        power_limits["max_power_source_target"] = np.array([max_power_st])
    if max_power_ts is not None:
        power_limits["max_power_target_source"] = np.array([max_power_ts])

    efficiency: dict[str, Any] = {}
    if efficiency_st is not None:
        efficiency["efficiency_source_target"] = np.array([efficiency_st])
    if efficiency_ts is not None:
        efficiency["efficiency_target_source"] = np.array([efficiency_ts])

    config: dict[str, Any] = {
        "element_type": ElementType.EV,
        "name": name,
        "connection": as_connection_target("switchboard"),
        "vehicle": {
            "capacity": np.array([capacity]),
            "energy_per_distance": energy_per_distance,
            "current_soc": current_soc,
        },
        "charging": charging,
        "power_limits": power_limits,
        "efficiency": efficiency,
    }
    if public_charging_price is not None:
        config["public_charging"] = {"public_charging_price": np.array([public_charging_price])}

    return EvConfigData(**config)


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Basic EV with charge rate only",
        "data": _make_ev_config(
            capacity=60.0,
            current_soc=80.0,
            max_charge_rate=7.4,
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "my_ev",
                "capacity": [60.0],
                "initial_charge": 48.0,  # 80% of 60
                "salvage_value": 0.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "my_ev:connection",
                "source": "my_ev",
                "target": "switchboard",
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": None,
                        "efficiency_target_source": None,
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 0.0,
                        "max_power_target_source": [7.4],
                    },
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "my_ev:trip",
                "capacity": [0.0],
                "initial_charge": 0.0,
                "salvage_value": 0.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "my_ev:trip_connection",
                "source": "my_ev",
                "target": "my_ev:trip",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": 0.0,
                        "max_power_target_source": None,
                    },
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": "my_ev:public_grid",
                "is_source": True,
                "is_sink": False,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "my_ev:public_connection",
                "source": "my_ev:public_grid",
                "target": "my_ev:trip",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": None,
                        "max_power_target_source": None,
                    },
                },
            },
        ],
    },
    {
        "description": "EV with public charging price",
        "data": _make_ev_config(
            capacity=60.0,
            current_soc=50.0,
            max_charge_rate=7.4,
            max_discharge_rate=5.0,
            public_charging_price=0.30,
            efficiency_ts=0.95,
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "my_ev",
                "capacity": [60.0],
                "initial_charge": 30.0,  # 50% of 60
                "salvage_value": 0.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "my_ev:connection",
                "source": "my_ev",
                "target": "switchboard",
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": None,
                        "efficiency_target_source": [0.95],
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [5.0],
                        "max_power_target_source": [7.4],
                    },
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "my_ev:trip",
                "capacity": [0.0],
                "initial_charge": 0.0,
                "salvage_value": 0.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "my_ev:trip_connection",
                "source": "my_ev",
                "target": "my_ev:trip",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [5.0],
                        "max_power_target_source": None,
                    },
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": "my_ev:public_grid",
                "is_source": True,
                "is_sink": False,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "my_ev:public_connection",
                "source": "my_ev:public_grid",
                "target": "my_ev:trip",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": None,
                        "max_power_target_source": None,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": [0.30],
                        "price_target_source": None,
                    },
                },
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Basic EV outputs with charge and discharge",
        "name": "my_ev",
        "config": _make_ev_config(capacity=60.0, current_soc=80.0, max_charge_rate=7.4),
        "model_outputs": {
            "my_ev": {
                model_battery.BATTERY_POWER_CHARGE: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="-"
                ),
                model_battery.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.0,), direction="+"
                ),
                model_battery.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(53.0,)),
                model_battery.BATTERY_POWER_BALANCE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.12,)
                ),
            },
            "my_ev:connection": {
                CONNECTION_SEGMENTS: {
                    "power_limit": {
                        POWER_LIMIT_TARGET_SOURCE: OutputData(
                            type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)
                        ),
                        POWER_LIMIT_SOURCE_TARGET: OutputData(
                            type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)
                        ),
                    }
                },
            },
            "my_ev:trip": {
                model_battery.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0,)),
            },
            "my_ev:public_connection": {
                CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.0,), direction="+"
                ),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            EV_DEVICE_EV: {
                EV_POWER_CHARGE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(5.0,), direction="-"),
                EV_POWER_DISCHARGE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.0,), direction="+"),
                EV_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(53.0,)),
                EV_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-5.0,), direction=None),
                EV_STATE_OF_CHARGE: OutputData(
                    type=OutputType.STATE_OF_CHARGE,
                    unit="%",
                    values=(pytest.approx(88.333, rel=1e-2),),
                    direction=None,
                ),
                EV_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.12,)),
                EV_TRIP_ENERGY_REQUIRED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.0,)),
                EV_PUBLIC_CHARGE_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(0.0,), direction="+"),
                EV_POWER_MAX_DISCHARGE_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                EV_POWER_MAX_CHARGE_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES[ElementType.EV]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES[ElementType.EV]
    result = entry.outputs(case["name"], case["model_outputs"], config=case["config"], periods=case["periods"])
    assert result == case["outputs"]
