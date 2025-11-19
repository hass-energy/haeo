"""Test data and factories for Battery element."""

from typing import Any

from custom_components.haeo.model.battery import Battery

VALID_CASES = [
    {
        "description": "Battery charging from infinite source",
        "factory": Battery,
        "data": {
            "name": "battery_charging",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 20.0,
            "min_charge_percentage": 10.0,
            "max_charge_percentage": 90.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": -0.1,  # Negative cost = benefit for consuming (encourages charging)
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (5.0, 2.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (2.0, 7.0, 9.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (20.0, 70.0, 90.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (1.0, 6.0, 8.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (5.0, 2.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.001, 0.002, 0.003)},
        },
    },
    {
        "description": "Battery discharging to infinite sink",
        "factory": Battery,
        "data": {
            "name": "battery_discharging",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 80.0,
            "min_charge_percentage": 10.0,
            "max_charge_percentage": 90.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 3.0,
            "efficiency": 95.0,
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": 0.1,  # Positive cost = benefit for providing power (encourages discharging)
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (3.0, 1.0, 3.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (8.0, 5.0, 4.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (80.0, 50.0, 40.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (7.0, 4.0, 3.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (3.0, 1.0, 3.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.001, 0.002, 0.003)},
        },
    },
    {
        "description": "Battery with fixed load pattern",
        "factory": Battery,
        "data": {
            "name": "battery_fixed",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 100.0,
        },
        "inputs": {
            "power": [2.0, -1.0, 1.0],  # Positive=charge, negative=discharge
            "cost": 0.0,
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 1.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 1.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 7.0, 6.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 70.0, 60.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (4.0, 6.0, 5.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 1.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 1.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.001, 0.002, 0.003)},
        },
    },
    {
        "description": "Battery with overcharge - not used due to high cost",
        "factory": Battery,
        "data": {
            "name": "battery_overcharge_expensive",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 75.0,  # Start near max
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "overcharge_percentage": 95.0,
            "overcharge_cost": 10.0,  # Very expensive - more than external benefit
            "max_charge_power": 10.0,
            "efficiency": 100.0,  # Perfect efficiency to simplify
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": -0.1,  # 0.1 $/kWh benefit for charging
        },
        "expected_outputs": {
            # Should charge to 80% but not beyond due to high overcharge cost
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (7.5, 8.0, 8.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (75.0, 80.0, 80.0)},
            "section_overcharge_energy": {"type": "energy", "unit": "kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery with overcharge - used when economical",
        "factory": Battery,
        "data": {
            "name": "battery_overcharge_cheap",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 75.0,  # Start near max
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "overcharge_percentage": 95.0,
            "overcharge_cost": 0.01,  # Cheap - less than external benefit
            "max_charge_power": 10.0,
            "efficiency": 100.0,  # Perfect efficiency to simplify
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": -0.1,  # 0.1 $/kWh benefit for charging
        },
        "expected_outputs": {
            # Should charge to 80% then continue to 95% using overcharge
            # Optimizer may split charging across periods due to costs
            # Energy values show state at START of each period
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 1.5)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (7.5, 8.0, 8.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (75.0, 80.0, 80.0)},
            "section_overcharge_energy": {"type": "energy", "unit": "kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery with undercharge - avoided due to high cost",
        "factory": Battery,
        "data": {
            "name": "battery_undercharge_expensive",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 25.0,  # Start near min
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "undercharge_percentage": 5.0,
            "undercharge_cost": 10.0,  # Very expensive - more than external benefit
            "max_discharge_power": 10.0,
            "efficiency": 100.0,  # Perfect efficiency to simplify
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": 0.1,  # 0.1 $/kWh benefit for discharging
        },
        "expected_outputs": {
            # Should discharge from normal section (0.5 kWh available) but not touch undercharge
            # Battery starts at 25% with undercharge section full (1.5 kWh) and normal section at 0.5 kWh
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.5)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (2.5, 2.5, 2.5)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (25.0, 25.0, 25.0)},
            "section_undercharge_energy": {"type": "energy", "unit": "kWh", "values": (1.5, 1.5, 1.5)},
        },
    },
    {
        "description": "Battery with undercharge - used when economical",
        "factory": Battery,
        "data": {
            "name": "battery_undercharge_cheap",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 25.0,  # Start near min
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "undercharge_percentage": 5.0,
            "undercharge_cost": 0.01,  # Cheap - less than external benefit
            "max_discharge_power": 10.0,
            "efficiency": 100.0,  # Perfect efficiency to simplify
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": 0.1,  # 0.1 $/kWh benefit for discharging
        },
        "expected_outputs": {
            # Should discharge normal section then continue into undercharge section
            # Battery starts at 25% with undercharge full (1.5 kWh) and normal at 0.5 kWh
            # Scaled incentives encourage proper ordering: normal discharges first
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 1.5)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (2.5, 2.0, 2.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (25.0, 20.0, 20.0)},
            "section_undercharge_energy": {"type": "energy", "unit": "kWh", "values": (1.5, 1.5, 1.5)},
        },
    },
    {
        "description": "Battery with both undercharge and overcharge sections",
        "factory": Battery,
        "data": {
            "name": "battery_both_sections",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "undercharge_percentage": 5.0,
            "overcharge_percentage": 95.0,
            "undercharge_cost": 0.01,
            "overcharge_cost": 0.01,
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency": 100.0,
        },
        "inputs": {
            # Test that both sections can coexist without conflicts
            "power": [None, None, None],
            "cost": 0.0,
        },
        "expected_outputs": {
            # Early charge incentive causes charging to 80% in period 0
            # Both sections coexist without conflicts
            "power_consumed": {"type": "power", "unit": "kW", "values": (3.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 8.0, 8.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 80.0, 80.0)},
            "section_undercharge_energy": {"type": "energy", "unit": "kWh", "values": (1.5, 1.5, 1.5)},
            "section_overcharge_energy": {"type": "energy", "unit": "kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery with changing thresholds - energy redistributes between sections",
        "factory": Battery,
        "data": {
            "name": "battery_threshold_change",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 75.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": [80.0, 70.0, 70.0],  # Threshold drops in period 1
            "overcharge_percentage": 95.0,
            "overcharge_cost": 0.05,
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency": 100.0,
        },
        "inputs": {
            "power": [0.0, 0.0, 0.0],  # No external power flow
            "cost": 0.0,
        },
        "expected_outputs": {
            # Battery starts at 75% in normal range
            # When threshold drops to 70%, the 5% (0.5 kWh) moves to overcharge section
            # Total energy stays at 7.5 kWh, but section distribution changes
            # Small power flows in period 0 may occur due to optimizer handling constraint changes
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (7.5, 7.5, 7.5)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (75.0, 75.0, 75.0)},
            "section_overcharge_energy": {"type": "energy", "unit": "kWh", "values": (0.0, 0.5, 0.5)},
        },
    },
]

INVALID_CASES: list[dict[str, Any]] = [
    {
        "description": "Battery capacity array length mismatch",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": [10.0, 10.0],  # Only 2 values for 3 periods
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
    {
        "description": "Battery min_charge_percentage greater than max_charge_percentage",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 80.0,  # Greater than max
            "max_charge_percentage": 20.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "min_charge_percentage .* must be less than max_charge_percentage",
    },
    {
        "description": "Battery undercharge_percentage greater than min_charge_percentage",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "undercharge_percentage": 30.0,  # Greater than min
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "undercharge_percentage .* must be less than min_charge_percentage",
    },
    {
        "description": "Battery max_charge_percentage greater than overcharge_percentage",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "overcharge_percentage": 70.0,  # Less than max
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "overcharge_percentage .* must be greater than max_charge_percentage",
    },
]
