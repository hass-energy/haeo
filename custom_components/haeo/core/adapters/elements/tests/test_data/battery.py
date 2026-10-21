"""Adapter mapping cases for the battery element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.battery import (
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
from custom_components.haeo.core.model import battery as battery_model
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    connection,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData

from . import CreateCase, OutputsCase

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Battery with charge limits",
        "data": BatteryConfigData(
            element_type=ElementType.BATTERY,
            name="battery_main",
            connection=as_connection_target("network"),
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
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            advanced={"charge_limit_cost": 100.0},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery_main",
                "capacity": [10.0, 10.0],
                "initial_charge": 5.0,
                "min_charge": [1.0, 1.0],
                "max_charge": [9.0, 9.0],
                "salvage_value": 0.0,
                "charge_limit_cost": 100.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_main:discharge",
                "source": "battery_main",
                "target": "network",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                    "power_limit": {"segment_type": "power_limit", "max_power": [5.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_main:charge",
                "source": "network",
                "target": "battery_main",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [5.0]},
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                },
            },
        ],
    },
    {
        "description": "Battery with normal range only",
        "data": BatteryConfigData(
            element_type=ElementType.BATTERY,
            name="battery_normal",
            connection=as_connection_target("network"),
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
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            advanced={"charge_limit_cost": 100.0},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery_normal",
                "capacity": [10.0, 10.0],
                "min_charge": [0.0, 0.0],
                "max_charge": [10.0, 10.0],
                "initial_charge": 5.0,
                "salvage_value": 0.0,
                "charge_limit_cost": 100.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_normal:discharge",
                "source": "battery_normal",
                "target": "network",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                    "power_limit": {"segment_type": "power_limit", "max_power": [5.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_normal:charge",
                "source": "network",
                "target": "battery_normal",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [5.0]},
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                },
            },
        ],
    },
    {
        "description": "Battery with salvage value",
        "data": BatteryConfigData(
            element_type=ElementType.BATTERY,
            name="battery_salvage",
            connection=as_connection_target("network"),
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
                "salvage_value": 0.05,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            advanced={"charge_limit_cost": 100.0},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "battery_salvage",
                "capacity": [8.0, 8.0],
                "min_charge": [0.0, 0.0],
                "max_charge": [8.0, 8.0],
                "initial_charge": 4.0,
                "salvage_value": 0.05,
                "charge_limit_cost": 100.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_salvage:discharge",
                "source": "battery_salvage",
                "target": "network",
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                    "power_limit": {"segment_type": "power_limit", "max_power": [4.0]},
                },
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "battery_salvage:charge",
                "source": "network",
                "target": "battery_salvage",
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": [4.0]},
                    "efficiency": {"segment_type": "efficiency", "efficiency": [0.95]},
                },
            },
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Battery normal range outputs",
        "data": BatteryConfigData(
            element_type=ElementType.BATTERY,
            name="battery_no_balance",
            connection=as_connection_target("network"),
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
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            advanced={"charge_limit_cost": 100.0},
        ),
        "model_outputs": {
            "battery_no_balance": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_no_balance:discharge": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.5,), direction="+"
                ),
            },
            "battery_no_balance:charge": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="+"
                ),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            BATTERY_DEVICE_BATTERY: {
                BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                BATTERY_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                BATTERY_STATE_OF_CHARGE: OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.4, 0.4)),
                BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
                BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
            },
        },
    },
    {
        "description": "Battery charge connection pruned - charge carries no flow",
        "data": BatteryConfigData(
            element_type=ElementType.BATTERY,
            name="battery_no_balance",
            connection=as_connection_target("network"),
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
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            advanced={"charge_limit_cost": 100.0},
        ),
        "model_outputs": {
            "battery_no_balance": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_no_balance:discharge": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.5,), direction="+"
                ),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            BATTERY_DEVICE_BATTERY: {
                BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.0,), direction="-"),
                BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                BATTERY_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction=None),
                BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(4.0, 4.0)),
                BATTERY_STATE_OF_CHARGE: OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.4, 0.4)),
                BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
                BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
            },
        },
    },
    {
        "description": "Battery outputs report stored energy as held",
        "data": BatteryConfigData(
            element_type=ElementType.BATTERY,
            name="battery_with_thresholds",
            connection=as_connection_target("network"),
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
                "salvage_value": 0.0,
            },
            efficiency={
                "efficiency_source_target": np.array([0.95]),
                "efficiency_target_source": np.array([0.95]),
            },
            advanced={"charge_limit_cost": 100.0},
        ),
        "model_outputs": {
            "battery_with_thresholds": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(3.5, 3.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            "battery_with_thresholds:discharge": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(0.5,), direction="+"
                ),
            },
            "battery_with_thresholds:charge": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="+"
                ),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            BATTERY_DEVICE_BATTERY: {
                BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                BATTERY_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(3.5, 3.5)),
                BATTERY_STATE_OF_CHARGE: OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.35, 0.35)),
                BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1,)),
                BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True
                ),
                BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
            },
        },
    },
]
