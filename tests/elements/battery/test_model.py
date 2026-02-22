"""Tests for battery element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.adapters.elements.battery import (
    BATTERY_DEVICE_BATTERY,
    BATTERY_ENERGY_IN_FLOW,
    BATTERY_ENERGY_OUT_FLOW,
    BATTERY_ENERGY_STORED,
    BATTERY_POWER_ACTIVE,
    BATTERY_POWER_BALANCE,
    BATTERY_POWER_CHARGE,
    BATTERY_POWER_DISCHARGE,
    BATTERY_SOC_MAX,
    BATTERY_SOC_MIN,
    BATTERY_STATE_OF_CHARGE,
)
from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.schema.elements.battery import BatteryConfigData
from custom_components.haeo.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.model import battery as battery_model
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
)
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema import as_connection_target
from tests.util.normalize import normalize_for_compare


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: BatteryConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    data: BatteryConfigData
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Battery with SOC pricing thresholds",
        "data": BatteryConfigData(
            element_type="battery",
            common={
                "name": "battery_main",
                "connection": as_connection_target("network"),
            },
            storage={
                "capacity": np.array([10.0, 10.0]),
                "initial_charge_percentage": 0.5,
            },
            limits={
                "min_charge_percentage": np.array([0.1, 0.1]),
                "max_charge_percentage": np.array([0.9, 0.9]),
            },
            power_limits={
                "max_power_source_target": np.array([5.0]),
                "max_power_target_source": np.array([5.0]),
            },
            pricing={
                "price_source_target": np.array([0.03]),
                "price_target_source": np.array([0.01]),
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            partitioning={},
            undercharge={
                "percentage": np.array([0.05, 0.05]),
                "cost": np.array([0.03]),
            },
            overcharge={
                "percentage": np.array([0.95, 0.95]),
                "cost": np.array([0.04]),
            },
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery_main",
                "capacity": [9.0, 9.0],
                "initial_charge": 4.5,
                "salvage_value": 0.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_main:connection",
                "source": "battery_main",
                "target": "network",
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": [0.95],
                        "efficiency_target_source": [0.95],
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [5.0],
                        "max_power_target_source": [5.0],
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": [0.04],
                        "price_target_source": [-0.01],
                    },
                    "soc_pricing": {
                        "segment_type": "soc_pricing",
                        "discharge_energy_threshold": [0.5],
                        "charge_capacity_threshold": [8.5],
                        "discharge_energy_price": [0.03],
                        "charge_capacity_price": [0.04],
                    },
                },
            },
        ],
    },
    {
        "description": "Battery with normal range only",
        "data": BatteryConfigData(
            element_type="battery",
            common={
                "name": "battery_normal",
                "connection": as_connection_target("network"),
            },
            storage={
                "capacity": np.array([10.0, 10.0]),
                "initial_charge_percentage": 0.5,
            },
            limits={
                "min_charge_percentage": np.array([0.0, 0.0]),
                "max_charge_percentage": np.array([1.0, 1.0]),
            },
            power_limits={
                "max_power_source_target": np.array([5.0]),
                "max_power_target_source": np.array([5.0]),
            },
            pricing={
                "price_source_target": np.array([0.003]),
                "price_target_source": np.array([0.001]),
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            partitioning={},
            undercharge={},
            overcharge={},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery_normal",
                "capacity": [10.0, 10.0],
                "initial_charge": 5.0,
                "salvage_value": 0.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_normal:connection",
                "source": "battery_normal",
                "target": "network",
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": [0.95],
                        "efficiency_target_source": [0.95],
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [5.0],
                        "max_power_target_source": [5.0],
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": [0.004],
                        "price_target_source": [-0.001],
                    },
                },
            },
        ],
    },
    {
        "description": "Battery with salvage value",
        "data": BatteryConfigData(
            element_type="battery",
            common={
                "name": "battery_salvage",
                "connection": as_connection_target("network"),
            },
            storage={
                "capacity": np.array([8.0, 8.0]),
                "initial_charge_percentage": 0.5,
            },
            limits={
                "min_charge_percentage": np.array([0.0, 0.0]),
                "max_charge_percentage": np.array([1.0, 1.0]),
            },
            power_limits={
                "max_power_source_target": np.array([4.0]),
                "max_power_target_source": np.array([4.0]),
            },
            pricing={
                "price_source_target": np.array([0.02]),
                "price_target_source": np.array([0.01]),
                "salvage_value": 0.05,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            partitioning={},
            undercharge={},
            overcharge={},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery_salvage",
                "capacity": [8.0, 8.0],
                "initial_charge": 4.0,
                "salvage_value": 0.05,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_salvage:connection",
                "source": "battery_salvage",
                "target": "network",
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": [0.95],
                        "efficiency_target_source": [0.95],
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": [4.0],
                        "max_power_target_source": [4.0],
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": [0.03],
                        "price_target_source": [-0.01],
                    },
                },
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Battery normal range outputs",
        "name": "battery_no_balance",
        "data": BatteryConfigData(
            element_type="battery",
            common={
                "name": "battery_no_balance",
                "connection": as_connection_target("network"),
            },
            storage={
                "capacity": np.array([10.0, 10.0]),
                "initial_charge_percentage": 0.5,
            },
            limits={
                "min_charge_percentage": np.array([0.0, 0.0]),
                "max_charge_percentage": np.array([1.0, 1.0]),
            },
            power_limits={
                "max_power_source_target": np.array([5.0]),
                "max_power_target_source": np.array([5.0]),
            },
            pricing={
                "price_source_target": np.array([0.003]),
                "price_target_source": np.array([0.001]),
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            partitioning={},
            undercharge={},
            overcharge={},
        ),
        "model_outputs": {
            "battery_no_balance": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
        },
        "outputs": {
            BATTERY_DEVICE_BATTERY: {
                BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                BATTERY_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                BATTERY_STATE_OF_CHARGE: OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.4, 0.4)),
                BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
                BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
            },
        },
    },
    {
        "description": "Battery outputs include undercharge offset",
        "name": "battery_with_thresholds",
        "data": BatteryConfigData(
            element_type="battery",
            common={
                "name": "battery_with_thresholds",
                "connection": as_connection_target("network"),
            },
            storage={
                "capacity": np.array([10.0, 10.0]),
                "initial_charge_percentage": 0.5,
            },
            limits={
                "min_charge_percentage": np.array([0.1, 0.1]),
                "max_charge_percentage": np.array([0.9, 0.9]),
            },
            power_limits={
                "max_power_source_target": np.array([5.0]),
                "max_power_target_source": np.array([5.0]),
            },
            pricing={
                "price_source_target": np.array([0.003]),
                "price_target_source": np.array([0.001]),
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            partitioning={},
            undercharge={
                "percentage": np.array([0.05, 0.05]),
                "cost": np.array([0.03]),
            },
            overcharge={
                "percentage": np.array([0.95, 0.95]),
                "cost": np.array([0.04]),
            },
        ),
        "model_outputs": {
            "battery_with_thresholds": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(3.5, 3.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
        },
        "outputs": {
            BATTERY_DEVICE_BATTERY: {
                BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                BATTERY_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                BATTERY_STATE_OF_CHARGE: OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.4, 0.4)),
                BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
                BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
            },
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["battery"]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["battery"]
    result = entry.outputs(case["name"], case["model_outputs"], config=case["data"])
    assert result == case["outputs"]
