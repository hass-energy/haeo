"""Tests for battery element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import battery as battery_element
from custom_components.haeo.elements.battery import BatteryConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model import energy_storage as energy_storage_model
from custom_components.haeo.model import energy_balance_connection as balance_model
from custom_components.haeo.model import node as node_model
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for create_model_elements."""

    description: str
    data: BatteryConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    data: BatteryConfigData
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Battery with all sections",
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_main",
            connection="network",
            capacity=[10.0],
            initial_charge_percentage=[50.0],
            min_charge_percentage=[10.0],
            max_charge_percentage=[90.0],
            efficiency=[95.0],
            max_charge_power=[5.0],
            max_discharge_power=[5.0],
            early_charge_incentive=[0.01],
            discharge_cost=[0.02],
            undercharge_percentage=[5.0],
            overcharge_percentage=[95.0],
            undercharge_cost=[0.03],
            overcharge_cost=[0.04],
        ),
        "model": [
            {
                "element_type": "energy_storage",
                "name": "battery_main:undercharge",
                "capacity": [0.5],
                "initial_charge": 0.5,
            },
            {
                "element_type": "energy_storage",
                "name": "battery_main:normal",
                "capacity": [8.0],
                "initial_charge": 4.0,
            },
            {
                "element_type": "energy_storage",
                "name": "battery_main:overcharge",
                "capacity": [0.49999999999999933],
                "initial_charge": 0.0,
            },
            {
                "element_type": "node",
                "name": "battery_main:node",
                "is_source": False,
                "is_sink": False,
            },
            # Undercharge connection: penalty on discharge (price_source_target)
            {
                "element_type": "connection",
                "name": "battery_main:undercharge:to_node",
                "source": "battery_main:undercharge",
                "target": "battery_main:node",
                "price_source_target": [0.03],
            },
            # Normal connection: no penalty
            {
                "element_type": "connection",
                "name": "battery_main:normal:to_node",
                "source": "battery_main:normal",
                "target": "battery_main:node",
                "price_source_target": None,
            },
            # Overcharge connection: penalty on charge (price_target_source)
            {
                "element_type": "connection",
                "name": "battery_main:overcharge:to_node",
                "source": "battery_main:overcharge",
                "target": "battery_main:node",
                "price_target_source": [0.04],
            },
            # Balance connection: undercharge -> normal
            {
                "element_type": "energy_balance_connection",
                "name": "battery_main:balance:undercharge:normal",
                "upper": "battery_main:normal",
                "lower": "battery_main:undercharge",
                "capacity_lower": [0.5],
            },
            # Balance connection: normal -> overcharge
            {
                "element_type": "energy_balance_connection",
                "name": "battery_main:balance:normal:overcharge",
                "upper": "battery_main:overcharge",
                "lower": "battery_main:normal",
                "capacity_lower": [8.0],
            },
            # Main connection to network
            {
                "element_type": "connection",
                "name": "battery_main:connection",
                "source": "battery_main:node",
                "target": "network",
                "efficiency_source_target": [95.0],
                "efficiency_target_source": [95.0],
                "max_power_source_target": [5.0],
                "max_power_target_source": [5.0],
                "price_target_source": [-0.01],
                "price_source_target": [0.03],  # early_discharge_incentive + discharge_cost
            },
        ],
    },
    {
        "description": "Battery with normal section only",
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_normal",
            connection="network",
            capacity=[10.0],
            initial_charge_percentage=[50.0],
            min_charge_percentage=[0.0],
            max_charge_percentage=[100.0],
            efficiency=[95.0],
            max_charge_power=[5.0],
            max_discharge_power=[5.0],
            early_charge_incentive=[0.001],
            discharge_cost=[0.002],
        ),
        "model": [
            {
                "element_type": "energy_storage",
                "name": "battery_normal:normal",
                "capacity": [10.0],
                "initial_charge": 5.0,
            },
            {
                "element_type": "node",
                "name": "battery_normal:node",
                "is_source": False,
                "is_sink": False,
            },
            # Normal connection: no penalty
            {
                "element_type": "connection",
                "name": "battery_normal:normal:to_node",
                "source": "battery_normal:normal",
                "target": "battery_normal:node",
                "price_source_target": None,
            },
            # Main connection to network
            {
                "element_type": "connection",
                "name": "battery_normal:connection",
                "source": "battery_normal:node",
                "target": "network",
                "efficiency_source_target": [95.0],
                "efficiency_target_source": [95.0],
                "max_power_source_target": [5.0],
                "max_power_target_source": [5.0],
                "price_target_source": [-0.001],
                "price_source_target": [0.003],  # early_discharge_incentive + discharge_cost
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Battery normal section only",
        "name": "battery_no_balance",
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_no_balance",
            connection="network",
            capacity=[10.0],
            initial_charge_percentage=[50.0],
            min_charge_percentage=[0.0],
            max_charge_percentage=[100.0],
            efficiency=[95.0],
            max_charge_power=[5.0],
            max_discharge_power=[5.0],
            early_charge_incentive=[0.001],
            discharge_cost=[0.002],
        ),
        "model_outputs": {
            "battery_no_balance:normal": {
                energy_storage_model.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                energy_storage_model.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                energy_storage_model.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_no_balance:node": {},
            "battery_no_balance:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.5,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="-"),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(40.0, 40.0)),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
            },
        },
    },
    {
        "description": "Battery with undercharge and overcharge sections and balance connections",
        "name": "battery_all_sections",
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_all_sections",
            connection="network",
            capacity=[10.0],
            initial_charge_percentage=[50.0],
            min_charge_percentage=[10.0],
            max_charge_percentage=[90.0],
            efficiency=[95.0],
            max_charge_power=[5.0],
            max_discharge_power=[5.0],
            early_charge_incentive=[0.001],
            discharge_cost=[0.002],
            undercharge_percentage=[5.0],
            overcharge_percentage=[95.0],
            undercharge_cost=[0.03],
            overcharge_cost=[0.04],
        ),
        "model_outputs": {
            # Undercharge section
            "battery_all_sections:undercharge": {
                energy_storage_model.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.2,), direction="-"),
                energy_storage_model.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.1,), direction="+"),
                energy_storage_model.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.3, 0.4)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_all_sections:undercharge:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.1,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.2,), direction="-"),
            },
            # Normal section
            "battery_all_sections:normal": {
                energy_storage_model.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="-"),
                energy_storage_model.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.3,), direction="+"),
                energy_storage_model.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(3.0, 3.0)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_all_sections:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.3,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.5,), direction="-"),
            },
            # Overcharge section
            "battery_all_sections:overcharge": {
                energy_storage_model.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.3,), direction="-"),
                energy_storage_model.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.1,), direction="+"),
                energy_storage_model.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.2, 0.1)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_all_sections:overcharge:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.1,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.3,), direction="-"),
            },
            # Node with power balance
            "battery_all_sections:node": {
                node_model.NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
            },
            # Balance connections
            "battery_all_sections:balance:undercharge:normal": {
                balance_model.BALANCE_POWER_DOWN: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.05,)),
                balance_model.BALANCE_POWER_UP: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.02,)),
            },
            "battery_all_sections:balance:normal:overcharge": {
                balance_model.BALANCE_POWER_DOWN: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.03,)),
                balance_model.BALANCE_POWER_UP: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.01,)),
            },
        },
        # Expected outputs calculated as:
        # Total energy from sections: 0.3+3.0+0.2=3.5, 0.4+3.0+0.1=3.5
        # Add inaccessible energy (undercharge_percentage=5%): +0.5 -> 4.0, 4.0
        # SOC = (4.0/10)*100 = 40%
        # Power charge sum: 0.2+0.5+0.3=1.0, discharge sum: 0.1+0.3+0.1=0.5
        # Active power = discharge - charge = 0.5 - 1.0 = -0.5
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(40.0, 40.0)),
                battery_element.BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
            },
            battery_element.BATTERY_DEVICE_UNDERCHARGE: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.3, 0.4), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.2,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.1,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                # Undercharge (i=0) only has section above (normal), balance:undercharge:normal
                # Undercharge is lower, so power_down enters (0.05), power_up leaves (0.02)
                battery_element.BATTERY_BALANCE_POWER_DOWN: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.05,), advanced=True),
                battery_element.BATTERY_BALANCE_POWER_UP: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.02,), advanced=True),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(3.0, 3.0), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.3,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                # Normal gets power_down from balance:undercharge:normal (this section is upper, energy leaving) = 0.05
                #   + power_down from balance:normal:overcharge (this section is lower, energy entering) = 0.03 -> total = 0.08
                # Normal gets power_up from balance:undercharge:normal (this section is upper, energy entering) = 0.02
                #   + power_up from balance:normal:overcharge (this section is lower, energy leaving) = 0.01 -> total = 0.03
                battery_element.BATTERY_BALANCE_POWER_DOWN: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.08,), advanced=True),
                battery_element.BATTERY_BALANCE_POWER_UP: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.03,), advanced=True),
            },
            battery_element.BATTERY_DEVICE_OVERCHARGE: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(0.2, 0.1), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.3,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.1,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                # Overcharge (i=2) only has section below (normal), balance:normal:overcharge
                # Overcharge is upper, so power_down leaves (0.03), power_up enters (0.01)
                battery_element.BATTERY_BALANCE_POWER_DOWN: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.03,), advanced=True),
                battery_element.BATTERY_BALANCE_POWER_UP: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.01,), advanced=True),
            },
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_create_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["battery"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["battery"]
    result = entry.outputs(case["name"], case["model_outputs"], case["data"])
    assert result == case["outputs"]
