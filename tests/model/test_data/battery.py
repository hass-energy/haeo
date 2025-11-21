"""Test data and factories for Battery element."""

from custom_components.haeo.model.battery import Battery

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Battery charging with fixed input",
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
            "power": [5.0, 2.0, 0.0],  # Forced input to test efficiency
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (20.0, 67.5, 86.5, 86.5)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (2.0, 6.75, 8.65, 8.65)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (1.0, 5.75, 7.65, 7.65)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (4.75, 1.9, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (5.0, 2.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery discharging with fixed output",
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
            "max_discharge_power": 4.0,
            "efficiency": 95.0,
        },
        "inputs": {
            "power": [-3.0, -3.0, 0.0],  # Forced output to test efficiency
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_state_of_charge": {
                "type": "soc",
                "unit": "%",
                "values": (80.0, 48.421052632, 16.842105263, 16.842105263),
            },
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (8.0, 4.842105263, 1.684210526, 1.684210526)},
            "normal_energy_stored": {
                "type": "energy",
                "unit": "kWh",
                "values": (7.0, 3.842105263, 0.684210526, 0.684210526),
            },
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (3.157894737, 3.157894737, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (3.0, 3.0, 0.0)},
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
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            # Note: Time-slice constraint allows some cycling, but neutral cost prevents it.
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 70.0, 60.0, 70.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 7.0, 6.0, 7.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (4.0, 6.0, 5.0, 6.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 1.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 1.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 1.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 1.0, 0.0)},
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
            "initial_charge_percentage": 50.0,  # Start in middle
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "overcharge_percentage": 95.0,
            "overcharge_cost": 1.0,  # Expensive (1 $/kWh) - more than external benefit
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency": 100.0,  # Perfect efficiency to simplify
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            # Benefit for charging (0.1 $/kWh = 10 cents/kWh) - much larger than early_charge_incentive
            "input_cost": -0.1,
            "output_cost": 0.1,
        },
        "expected_outputs": {
            # With small external benefit (0.01 $/kWh), overcharge cost (1 $/kWh) is too high
            # Battery should charge to 80% (max normal) and stay there
            # Overcharge section should remain empty
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 80.0, 80.0, 80.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 8.0, 8.0, 8.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (3.0, 6.0, 6.0, 6.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (3.0, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "overcharge_energy_stored": {"type": "energy", "unit": "kWh", "values": (0.0, 0.0, 0.0, 0.0)},
            "overcharge_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "overcharge_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "overcharge_price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.999, 0.9995, 1.0)},
            "overcharge_price_production": {"type": "price", "unit": "$/kWh", "values": (0.003, 0.0045, 0.006)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (3.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
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
            "input_cost": -0.1,  # 0.1 $/kWh benefit for charging
            "output_cost": 0.1,
        },
        "expected_outputs": {
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (75.0, 95.0, 95.0, 95.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (7.5, 9.5, 9.5, 9.5)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (5.5, 6.0, 6.0, 6.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "overcharge_energy_stored": {"type": "energy", "unit": "kWh", "values": (0.0, 1.5, 1.5, 1.5)},
            "overcharge_power_consumed": {"type": "power", "unit": "kW", "values": (1.5, 0.0, 0.0)},
            "overcharge_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "overcharge_price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.009, 0.0095, 0.01)},
            "overcharge_price_production": {"type": "price", "unit": "$/kWh", "values": (0.003, 0.0045, 0.006)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
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
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency": 100.0,  # Perfect efficiency to simplify
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "input_cost": 0.1,  # 0.1 $/kWh benefit for discharging
            "output_cost": -0.1,
        },
        "expected_outputs": {
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (25.0, 20.0, 20.0, 20.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (2.5, 2.0, 2.0, 2.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (0.5, 0.0, 0.0, 0.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "undercharge_energy_stored": {"type": "energy", "unit": "kWh", "values": (1.5, 1.5, 1.5, 1.5)},
            "undercharge_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "undercharge_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "undercharge_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.003, -0.0015, 0.0)},
            "undercharge_price_production": {"type": "price", "unit": "$/kWh", "values": (10.001, 10.0015, 10.002)},
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
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency": 100.0,  # Perfect efficiency to simplify
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "input_cost": 0.1,  # 0.1 $/kWh benefit for discharging
            "output_cost": -0.1,
        },
        "expected_outputs": {
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (25.0, 5.0, 5.0, 5.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (2.5, 0.5, 0.5, 0.5)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (0.5, 0.0, 0.0, 0.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 0.0)},
            "undercharge_energy_stored": {"type": "energy", "unit": "kWh", "values": (1.5, 0.0, 0.0, 0.0)},
            "undercharge_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "undercharge_power_produced": {"type": "power", "unit": "kW", "values": (1.5, 0.0, 0.0)},
            "undercharge_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.003, -0.0015, 0.0)},
            "undercharge_price_production": {"type": "price", "unit": "$/kWh", "values": (0.011, 0.0115, 0.012)},
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
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 80.0, 80.0, 80.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 8.0, 8.0, 8.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (3.0, 6.0, 6.0, 6.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (3.0, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "overcharge_energy_stored": {"type": "energy", "unit": "kWh", "values": (0.0, 0.0, 0.0, 0.0)},
            "overcharge_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "overcharge_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "overcharge_price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.009, 0.0095, 0.01)},
            "overcharge_price_production": {"type": "price", "unit": "$/kWh", "values": (0.003, 0.0045, 0.006)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (3.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "undercharge_energy_stored": {"type": "energy", "unit": "kWh", "values": (1.5, 1.5, 1.5, 1.5)},
            "undercharge_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "undercharge_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "undercharge_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.003, -0.0015, 0.0)},
            "undercharge_price_production": {"type": "price", "unit": "$/kWh", "values": (0.011, 0.0115, 0.012)},
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
            "max_charge_percentage": [80.0, 70.0, 70.0, 70.0],  # Threshold drops in period 1
            "overcharge_percentage": 95.0,
            "overcharge_cost": 0.05,
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency": 100.0,
        },
        "inputs": {
            "power": [0.0, 0.0, 0.0],  # No external power flow
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (75.0, 75.0, 75.0, 75.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (7.5, 7.5, 7.5, 7.5)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (5.5, 5.0, 5.0, 5.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, -0.001, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.003, 0.004)},
            "overcharge_energy_stored": {"type": "energy", "unit": "kWh", "values": (0.0, 0.5, 0.5, 0.5)},
            "overcharge_power_consumed": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "overcharge_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "overcharge_price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.049, 0.0495, 0.05)},
            "overcharge_price_production": {"type": "price", "unit": "$/kWh", "values": (0.003, 0.0045, 0.006)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.5, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery with 50% efficiency - explicit efficiency validation",
        "factory": Battery,
        "data": {
            "name": "battery_efficiency_test",
            "period": 1.0,
            "n_periods": 2,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 10.0,
            "max_charge_percentage": 90.0,
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency": 50.0,  # 50% round-trip efficiency
        },
        "inputs": {
            "power": [8.0, 0.0],  # Forced input to test efficiency (max charge 4.0kWh / 0.5 = 8.0kW)
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 90.0, 90.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 9.0, 9.0)},
            "normal_energy_stored": {"type": "energy", "unit": "kWh", "values": (4.0, 8.0, 8.0)},
            "normal_power_consumed": {"type": "power", "unit": "kW", "values": (4.0, 0.0)},
            "normal_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
            "normal_price_consumption": {"type": "price", "unit": "$/kWh", "values": (-0.002, 0.0)},
            "normal_price_production": {"type": "price", "unit": "$/kWh", "values": (0.002, 0.004)},
            "power_consumed": {"type": "power", "unit": "kW", "values": (8.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = [
    {
        "description": "Battery min_charge_percentage greater than max_charge_percentage",
        "factory": Battery,
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
        "expected_error": "min_charge_ratio .* must be less than max_charge_ratio",
    },
    {
        "description": "Battery undercharge_percentage greater than min_charge_percentage",
        "factory": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "undercharge_percentage": 30.0,  # Greater than min
            "undercharge_cost": 0.01,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "undercharge_ratio .* must be less than min_charge_ratio",
    },
    {
        "description": "Battery max_charge_percentage greater than overcharge_percentage",
        "factory": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "overcharge_percentage": 70.0,  # Less than max
            "overcharge_cost": 0.01,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "overcharge_ratio .* must be greater than max_charge_ratio",
    },
    {
        "description": "Battery with empty forecast",
        "factory": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "max_charge_percentage": [],  # Empty list
        },
        "expected_error": "Sequence cannot be empty",
    },
]
