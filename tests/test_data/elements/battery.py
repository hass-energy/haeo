"""Test data for battery element configuration."""

from collections.abc import Sequence

from custom_components.haeo.elements import battery as battery_element
from custom_components.haeo.elements.battery import BatteryConfigData
from custom_components.haeo.model import battery as battery_model
from custom_components.haeo.model import battery_balance_connection as balance_connection
from custom_components.haeo.model import power_connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
    OUTPUT_TYPE_SOC,
)
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.node import NODE_POWER_BALANCE

from .types import (
    ElementConfigData,
    ElementConfigSchema,
    ElementValidCase,
    InvalidModelCase,
    InvalidSchemaCase,
)

# Single fully-typed pipeline case
VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
    {
        "description": "Adapter mapping battery case with all sections",
        "element_type": "battery",
        "schema": battery_element.BatteryConfigSchema(
            element_type="battery",
            name="battery_main",
            connection="network",
            capacity="sensor.battery_capacity",
            initial_charge_percentage="sensor.battery_initial_soc",
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=95.0,
            max_charge_power=["sensor.battery_max_charge_power"],
            max_discharge_power=["sensor.battery_max_discharge_power"],
            early_charge_incentive=0.01,
            discharge_cost=["sensor.battery_discharge_cost"],
            undercharge_percentage=5.0,
            overcharge_percentage=95.0,
            undercharge_cost=["sensor.battery_undercharge_cost"],
            overcharge_cost=["sensor.battery_overcharge_cost"],
        ),
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
            # Undercharge section
            {
                "element_type": "battery",
                "name": "battery_main:undercharge",
                "capacity": 0.5,  # (10% - 5%) * 10kWh
                "initial_charge": 0.5,  # 50% SOC fills undercharge completely
            },
            # Normal section
            {
                "element_type": "battery",
                "name": "battery_main:normal",
                "capacity": 8.0,  # (90% - 10%) * 10kWh
                "initial_charge": 4.0,  # Remaining from 50% SOC
            },
            # Overcharge section
            {
                "element_type": "battery",
                "name": "battery_main:overcharge",
                "capacity": 0.49999999999999933,  # (95% - 90%) * 10kWh (floating point precision)
                "initial_charge": 0.0,  # 50% SOC doesn't reach overcharge
            },
            # Internal node
            {
                "element_type": "node",
                "name": "battery_main:node",
                "is_source": False,
                "is_sink": False,
            },
            # Connection from undercharge section to node (penalty on discharge)
            {
                "element_type": "connection",
                "name": "battery_main:undercharge:to_node",
                "source": "battery_main:undercharge",
                "target": "battery_main:node",
                "price_source_target": [0.03],  # Undercharge penalty when discharging
            },
            # Connection from normal section to node (no penalty)
            {
                "element_type": "connection",
                "name": "battery_main:normal:to_node",
                "source": "battery_main:normal",
                "target": "battery_main:node",
                "price_source_target": None,  # No penalty for normal section
            },
            # Connection from overcharge section to node (penalty on charge)
            {
                "element_type": "connection",
                "name": "battery_main:overcharge:to_node",
                "source": "battery_main:overcharge",
                "target": "battery_main:node",
                "price_target_source": [0.04],  # Overcharge penalty when charging
            },
            # Balance connection between undercharge and normal
            {
                "element_type": "battery_balance_connection",
                "name": "battery_main:balance:undercharge:normal",
                "upper": "battery_main:normal",
                "lower": "battery_main:undercharge",
                "capacity_lower": 0.5,  # Undercharge capacity
            },
            # Balance connection between normal and overcharge
            {
                "element_type": "battery_balance_connection",
                "name": "battery_main:balance:normal:overcharge",
                "upper": "battery_main:overcharge",
                "lower": "battery_main:normal",
                "capacity_lower": 8.0,  # Normal capacity
            },
            # Connection from node to network with early charge incentive
            {
                "element_type": "connection",
                "name": "battery_main:connection",
                "source": "battery_main:node",
                "target": "network",
                "efficiency_source_target": 95.0,
                "efficiency_target_source": 95.0,
                "max_power_source_target": [5.0],
                "max_power_target_source": [5.0],
                "price_target_source": [-0.01],  # Charge early incentive
                "price_source_target": [0.03],  # Discharge early incentive + discharge_cost
            },
        ],
        "model_outputs": {
            # Undercharge section outputs
            "battery_main:undercharge": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.5, 0.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            # Normal section outputs
            "battery_main:normal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            # Overcharge section outputs
            "battery_main:overcharge": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.0, 0.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            # Node outputs
            "battery_main:node": {
                NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            },
            # Connection outputs (for prices)
            "battery_main:undercharge:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="-"),
                power_connection.CONNECTION_PRICE_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.03,), direction="+"),
            },
            "battery_main:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.5,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="-"),
            },
            "battery_main:overcharge:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="-"),
                power_connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.04,), direction="-"),
            },
            # Balance connection outputs
            "battery_main:balance:undercharge:normal": {
                balance_connection.BALANCE_POWER_DOWN: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="+"),
                balance_connection.BALANCE_POWER_UP: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="-"),
            },
            "battery_main:balance:normal:overcharge": {
                balance_connection.BALANCE_POWER_DOWN: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="+"),
                balance_connection.BALANCE_POWER_UP: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), direction="-"),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None),
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.0)),  # 0.5 inaccessible + 4.5 accessible
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(type=OUTPUT_TYPE_SOC, unit="%", values=(50.0, 50.0)),  # (0.5 inaccessible + 4.5) / 10 * 100
                battery_element.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            },
            battery_element.BATTERY_DEVICE_UNDERCHARGE: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.5, 0.5), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+", advanced=True),
                battery_element.BATTERY_DISCHARGE_PRICE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.03,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True),
                # Balance: only has connection above (to normal), so down enters from normal, up leaves to normal
                battery_element.BATTERY_BALANCE_POWER_DOWN: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), advanced=True),
                battery_element.BATTERY_BALANCE_POWER_UP: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), advanced=True),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True),
                # Balance: has connections both above (to overcharge) and below (to undercharge)
                battery_element.BATTERY_BALANCE_POWER_DOWN: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), advanced=True),
                battery_element.BATTERY_BALANCE_POWER_UP: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), advanced=True),
            },
            battery_element.BATTERY_DEVICE_OVERCHARGE: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.0, 0.0), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0,), direction="+", advanced=True),
                battery_element.BATTERY_CHARGE_PRICE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.04,), direction="-", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True),
                # Balance: only has connection below (to normal), so down enters from normal, up leaves to normal
                battery_element.BATTERY_BALANCE_POWER_DOWN: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), advanced=True),
                battery_element.BATTERY_BALANCE_POWER_UP: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0,), advanced=True),
            },
        },
    },
    {
        "description": "Adapter mapping battery with only normal section",
        "element_type": "battery",
        "schema": battery_element.BatteryConfigSchema(
            element_type="battery",
            name="battery_main",
            connection="network",
            capacity="sensor.battery_capacity",
            initial_charge_percentage="sensor.battery_initial_soc",
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=95.0,
            max_charge_power=["sensor.battery_max_charge_power"],
            max_discharge_power=["sensor.battery_max_discharge_power"],
        ),
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
            # Normal section only
            {
                "element_type": "battery",
                "name": "battery_main:normal",
                "capacity": 8.0,  # (90% - 10%) * 10kWh
                "initial_charge": 4.0,  # (50% - 10%) * 10kWh
            },
            # Internal node
            {
                "element_type": "node",
                "name": "battery_main:node",
                "is_source": False,
                "is_sink": False,
            },
            # Connection from normal section to node (no penalty for normal section)
            {
                "element_type": "connection",
                "name": "battery_main:normal:to_node",
                "source": "battery_main:normal",
                "target": "battery_main:node",
                "price_source_target": None,  # No penalty for normal section
            },
            # Connection from node to network with early charge incentive (default 0.001)
            {
                "element_type": "connection",
                "name": "battery_main:connection",
                "source": "battery_main:node",
                "target": "network",
                "efficiency_source_target": 95.0,
                "efficiency_target_source": 95.0,
                "max_power_source_target": [5.0],
                "max_power_target_source": [5.0],
                "price_target_source": [-0.001],  # Early charge incentive (default)
                "price_source_target": [0.001],  # Early discharge incentive (default)
            },
        ],
        "model_outputs": {
            # Normal section outputs
            "battery_main:normal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
            # Node outputs
            "battery_main:node": {
                NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            },
            # Connection outputs (no prices for normal section connection)
            "battery_main:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.5,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="-"),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None),
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.0)),  # 1.0 inaccessible + 4.0 accessible
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(type=OUTPUT_TYPE_SOC, unit="%", values=(50.0, 50.0)),  # (1.0 inaccessible + 4.0) / 10 * 100
                battery_element.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,), advanced=True),
            },
        },
    },
    {
        "description": "Battery early charging behavior with 4 periods",
        "element_type": "battery",
        "schema": battery_element.BatteryConfigSchema(
            element_type="battery",
            name="battery_early",
            connection="network",
            capacity="sensor.capacity",
            initial_charge_percentage="sensor.initial_soc",
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=100.0,  # 100% efficiency for simpler math
            max_charge_power=["sensor.max_charge"],
            max_discharge_power=["sensor.max_discharge"],
            early_charge_incentive=0.01,
        ),
        "data": BatteryConfigData(
            element_type="battery",
            name="battery_early",
            connection="network",
            capacity=[10.0, 10.0, 10.0, 10.0],  # 10 kWh over 4 periods
            initial_charge_percentage=[10.0, 10.0, 10.0, 10.0],  # Start at min (empty usable)
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=100.0,
            max_charge_power=[5.0, 5.0, 5.0, 5.0],
            max_discharge_power=[5.0, 5.0, 5.0, 5.0],
            early_charge_incentive=0.01,
        ),
        # Model elements - early charge incentive is now on main connection only
        "model": [
            {
                "element_type": "battery",
                "name": "battery_early:normal",
                "capacity": 8.0,  # (90% - 10%) * 10 kWh
                "initial_charge": 0.0,  # 10% SOC means empty usable capacity
            },
            {
                "element_type": "node",
                "name": "battery_early:node",
                "is_source": False,
                "is_sink": False,
            },
            {
                "element_type": "connection",
                "name": "battery_early:normal:to_node",
                "source": "battery_early:normal",
                "target": "battery_early:node",
                "price_source_target": None,  # No penalty for normal section
            },
            {
                "element_type": "connection",
                "name": "battery_early:connection",
                "source": "battery_early:node",
                "target": "network",
                "efficiency_source_target": 100.0,
                "efficiency_target_source": 100.0,
                "max_power_source_target": [5.0, 5.0, 5.0, 5.0],
                "max_power_target_source": [5.0, 5.0, 5.0, 5.0],
                # Early charge incentive: linspace(-0.01, 0, 4)
                "price_target_source": [
                    -0.01 + (0.01 * 0 / 3),  # -0.01
                    -0.01 + (0.01 * 1 / 3),  # -0.00666...
                    -0.01 + (0.01 * 2 / 3),  # -0.00333...
                    -0.01 + (0.01 * 3 / 3),  # 0.0
                ],
                # Early discharge incentive: linspace(0.01, 0.02, 4)
                "price_source_target": [
                    0.01 + (0.01 * 0 / 3),  # 0.01
                    0.01 + (0.01 * 1 / 3),  # 0.01333...
                    0.01 + (0.01 * 2 / 3),  # 0.01666...
                    0.01 + (0.01 * 3 / 3),  # 0.02
                ],
            },
        ],
        # Synthetic model_outputs for adapter mapping test
        "model_outputs": {
            "battery_early:normal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0, 0.0, 0.0, 0.0), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0, 0.0, 0.0, 1.0), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.0, 1.0, 1.0, 1.0, 0.0)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0, 0.0, 0.0, 0.0)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0)),
            },
            "battery_early:node": {
                NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0, 0.0, 0.0, 0.0)),
            },
            "battery_early:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.0, 0.0, 0.0, 1.0), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0, 0.0, 0.0, 0.0), direction="-"),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0, 0.0, 0.0, 0.0), direction="-"),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0, 0.0, 0.0, 1.0), direction="+"),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(-1.0, 0.0, 0.0, 1.0), direction=None),
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(1.0, 2.0, 2.0, 2.0, 1.0)),  # 1.0 inaccessible + accessible
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(type=OUTPUT_TYPE_SOC, unit="%", values=(10.0, 20.0, 20.0, 20.0, 10.0)),
                battery_element.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0, 0.0, 0.0, 0.0)),
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(0.0, 1.0, 1.0, 1.0, 0.0), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0, 0.0, 0.0, 0.0), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.0, 0.0, 0.0, 1.0), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0, 0.0, 0.0, 0.0), advanced=True),
            },
        },
        # Note: Full optimization tests for early charging behavior belong in
        # integration/scenario tests, not adapter mapping tests. The adapter mapping
        # tests verify that the linspace prices are correctly generated in the model.
    },
    {
        "description": "Battery without node power balance",
        "element_type": "battery",
        "schema": battery_element.BatteryConfigSchema(
            element_type="battery",
            name="battery_no_balance",
            connection="network",
            capacity="sensor.capacity",
            initial_charge_percentage="sensor.initial_soc",
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            efficiency=95.0,
            max_charge_power=["sensor.max_charge"],
            max_discharge_power=["sensor.max_discharge"],
        ),
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
                "price_source_target": None,  # No penalty for normal section
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
                "price_target_source": [-0.001],  # Early charge incentive (default)
                "price_source_target": [0.001],  # Early discharge incentive (default)
            },
        ],
        "model_outputs": {
            "battery_no_balance:normal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,)),
            },
            # Node outputs without NODE_POWER_BALANCE
            "battery_no_balance:node": {},
            # Connection outputs
            "battery_no_balance:normal:to_node": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(0.5,), direction="+"),
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="-"),
            },
        },
        "outputs": {
            battery_element.BATTERY_DEVICE_BATTERY: {
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_element.BATTERY_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None),
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.0)),
                battery_element.BATTERY_STATE_OF_CHARGE: OutputData(type=OUTPUT_TYPE_SOC, unit="%", values=(50.0, 50.0)),
                # No BATTERY_POWER_BALANCE since node_outputs doesn't have it
            },
            battery_element.BATTERY_DEVICE_NORMAL: {
                battery_element.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(4.0, 4.0), advanced=True),
                battery_element.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-", advanced=True),
                battery_element.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+", advanced=True),
                battery_element.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
                battery_element.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.0,), advanced=True),
            },
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = [
    {
        "description": "Battery min_charge_percentage greater than max_charge_percentage",
        "schema": {
            "element_type": "battery",
            "name": "test_battery",
            "connection": "network",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial_soc",
            "min_charge_percentage": 80.0,
            "max_charge_percentage": 20.0,
            "efficiency": 95.0,
        },
    },
]

# Invalid model parameter combinations - these are now validated at the adapter layer
# The model layer no longer validates these since it only handles single sections
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
