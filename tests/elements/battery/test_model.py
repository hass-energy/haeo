"""Tests for battery element model mapping.

These tests verify that battery adapters correctly:
1. Transform ConfigData into model element definitions
2. Map model outputs back to device outputs
"""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import battery as battery_element
from custom_components.haeo.elements.battery import BatteryConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model import battery as battery_model
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
    OUTPUT_TYPE_SOC,
)
from custom_components.haeo.model.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData


class ValidCase(TypedDict):
    """Test case structure for valid battery configurations."""

    description: str
    data: BatteryConfigData
    model: list[dict[str, Any]]
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


VALID_CASES: Sequence[ValidCase] = [
    {
        "description": "Battery with all sections (undercharge, normal, overcharge)",
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_main",
            connection="network",
            capacity=[10.0],
            initial_charge_percentage=[50.0],
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=95.0,
            max_charge_power=[5.0],
            max_discharge_power=[5.0],
            early_charge_incentive=0.01,
            discharge_cost=[0.02],
            undercharge_percentage=5.0,
            overcharge_percentage=95.0,
            undercharge_cost=[0.03],
            overcharge_cost=[0.04],
        ),
        "model": [
            {
                "element_type": "battery",
                "name": "battery_main:undercharge",
                "capacity": 0.5,
                "initial_charge": 0.5,
            },
            {
                "element_type": "battery",
                "name": "battery_main:normal",
                "capacity": 8.0,
                "initial_charge": 4.0,
            },
            {
                "element_type": "battery",
                "name": "battery_main:overcharge",
                "capacity": 0.49999999999999933,
                "initial_charge": 0.0,
            },
            {
                "element_type": "node",
                "name": "battery_main:node",
                "is_source": False,
                "is_sink": False,
            },
            {
                "element_type": "connection",
                "name": "battery_main:undercharge:to_node",
                "source": "battery_main:undercharge",
                "target": "battery_main:node",
                "price_target_source": [-0.03],
                "price_source_target": [0.04],
            },
            {
                "element_type": "connection",
                "name": "battery_main:normal:to_node",
                "source": "battery_main:normal",
                "target": "battery_main:node",
                "price_target_source": [-0.02],
                "price_source_target": [0.02],
            },
            {
                "element_type": "connection",
                "name": "battery_main:overcharge:to_node",
                "source": "battery_main:overcharge",
                "target": "battery_main:node",
                "price_target_source": [0.03],
                "price_source_target": [0.03],
            },
            {
                "element_type": "connection",
                "name": "battery_main:connection",
                "source": "battery_main:node",
                "target": "network",
                "efficiency_source_target": 95.0,
                "efficiency_target_source": 95.0,
                "max_power_source_target": [5.0],
                "max_power_target_source": [5.0],
                "price_source_target": [0.02],
            },
        ],
        "model_outputs": {
            "battery_main:undercharge": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.5, 0.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            "battery_main:normal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            "battery_main:overcharge": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.0, 0.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            "battery_main:node": {
                NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            },
            "battery_main:undercharge:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="+"
                ),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.03,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.04,), direction="+"
                ),
            },
            "battery_main:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.5,), direction="+"
                ),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.02,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.02,), direction="+"
                ),
            },
            "battery_main:overcharge:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="+"
                ),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.03,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.03,), direction="+"
                ),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None
                ),
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.0)
                ),
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(
                    type=OUTPUT_TYPE_SOC, unit="%", values=(50.0, 50.0)
                ),
                battery_element.BATTERY_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
            },
            battery_element.BATTERY_DEVICE_UNDERCHARGE: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.5, 0.5), advanced=True
                ),
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-", advanced=True
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+", advanced=True
                ),
                battery_element.BATTERY_CHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.03,), direction="-", advanced=True
                ),
                battery_element.BATTERY_DISCHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.04,), direction="+", advanced=True
                ),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True
                ),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True
                ),
                battery_element.BATTERY_SOC_MAX: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True
                ),
                battery_element.BATTERY_SOC_MIN: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True
                ),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0), advanced=True
                ),
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-", advanced=True
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+", advanced=True
                ),
                battery_element.BATTERY_CHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.02,), direction="-", advanced=True
                ),
                battery_element.BATTERY_DISCHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.02,), direction="+", advanced=True
                ),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True
                ),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True
                ),
                battery_element.BATTERY_SOC_MAX: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True
                ),
                battery_element.BATTERY_SOC_MIN: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True
                ),
            },
            battery_element.BATTERY_DEVICE_OVERCHARGE: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.0, 0.0), advanced=True
                ),
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-", advanced=True
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+", advanced=True
                ),
                battery_element.BATTERY_CHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.03,), direction="-", advanced=True
                ),
                battery_element.BATTERY_DISCHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.03,), direction="+", advanced=True
                ),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True
                ),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True
                ),
                battery_element.BATTERY_SOC_MAX: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True
                ),
                battery_element.BATTERY_SOC_MIN: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True
                ),
            },
        },
    },
    {
        "description": "Battery with only normal section",
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_main",
            connection="network",
            capacity=[10.0],
            initial_charge_percentage=[50.0],
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=95.0,
            max_charge_power=[5.0],
            max_discharge_power=[5.0],
        ),
        "model": [
            {
                "element_type": "battery",
                "name": "battery_main:normal",
                "capacity": 8.0,
                "initial_charge": 4.0,
            },
            {
                "element_type": "node",
                "name": "battery_main:node",
                "is_source": False,
                "is_sink": False,
            },
            {
                "element_type": "connection",
                "name": "battery_main:normal:to_node",
                "source": "battery_main:normal",
                "target": "battery_main:node",
                "price_target_source": [-0.002],
                "price_source_target": [0.002],
            },
            {
                "element_type": "connection",
                "name": "battery_main:connection",
                "source": "battery_main:node",
                "target": "network",
                "efficiency_source_target": 95.0,
                "efficiency_target_source": 95.0,
                "max_power_source_target": [5.0],
                "max_power_target_source": [5.0],
                "price_source_target": None,
            },
        ],
        "model_outputs": {
            "battery_main:normal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            "battery_main:node": {
                NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            },
            "battery_main:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.5,), direction="+"
                ),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.002,), direction="-"
                ),
                power_connection.CONNECTION_PRICE_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.002,), direction="+"
                ),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None
                ),
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.0)
                ),
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(
                    type=OUTPUT_TYPE_SOC, unit="%", values=(50.0, 50.0)
                ),
                battery_element.BATTERY_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0), advanced=True
                ),
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-", advanced=True
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+", advanced=True
                ),
                battery_element.BATTERY_CHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(-0.002,), direction="-", advanced=True
                ),
                battery_element.BATTERY_DISCHARGE_PRICE: OutputData(
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.002,), direction="+", advanced=True
                ),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True
                ),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True
                ),
                battery_element.BATTERY_SOC_MAX: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True
                ),
                battery_element.BATTERY_SOC_MIN: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True
                ),
            },
        },
    },
    {
        "description": "Battery without node power balance",
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_no_balance",
            connection="network",
            capacity=[10.0],
            initial_charge_percentage=[50.0],
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=95.0,
            max_charge_power=[5.0],
            max_discharge_power=[5.0],
        ),
        "model": [
            {
                "element_type": "battery",
                "name": "battery_no_balance:normal",
                "capacity": 8.0,
                "initial_charge": 4.0,
            },
            {
                "element_type": "node",
                "name": "battery_no_balance:node",
                "is_source": False,
                "is_sink": False,
            },
            {
                "element_type": "connection",
                "name": "battery_no_balance:normal:to_node",
                "source": "battery_no_balance:normal",
                "target": "battery_no_balance:node",
                "price_target_source": [-0.002],
                "price_source_target": [0.002],
            },
            {
                "element_type": "connection",
                "name": "battery_no_balance:connection",
                "source": "battery_no_balance:node",
                "target": "network",
                "efficiency_source_target": 95.0,
                "efficiency_target_source": 95.0,
                "max_power_source_target": [5.0],
                "max_power_target_source": [5.0],
                "price_source_target": None,
            },
        ],
        "model_outputs": {
            "battery_no_balance:normal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_no_balance:node": {},
            "battery_no_balance:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.5,), direction="+"
                ),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="-"
                ),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None
                ),
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.0)
                ),
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(
                    type=OUTPUT_TYPE_SOC, unit="%", values=(50.0, 50.0)
                ),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0), advanced=True
                ),
                battery_element.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-", advanced=True
                ),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+", advanced=True
                ),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                battery_element.BATTERY_SOC_MAX: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                battery_element.BATTERY_SOC_MIN: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
            },
        },
    },
]


def _case_id(case: ValidCase) -> str:
    return case["description"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_create_model_elements(case: ValidCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["battery"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_outputs_mapping(case: ValidCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["battery"]
    result = entry.outputs(case["data"]["name"], case["model_outputs"], case["data"])
    assert result == case["outputs"]
