"""Test data and factories for BatteryBalanceConnection element."""

from custom_components.haeo.model.battery_balance_connection import BatteryBalanceConnection

from .connection_types import ConnectionTestCase

# Note: BatteryBalanceConnection requires integration with Battery elements,
# so it cannot use the standard ConnectionTestCase pattern directly.
# These test cases define the parameters and expected behavior for integration tests.

VALID_CASES: list[ConnectionTestCase] = [
    {
        "description": "Balance connection with no capacity change",
        "factory": BatteryBalanceConnection,
        "data": {
            "name": "balance_constant",
            "periods": [1.0] * 3,
            "upper": "normal_battery",
            "lower": "undercharge_battery",
            "capacity_lower": [5.0, 5.0, 5.0, 5.0],  # T+1 fence-posted, no change
        },
        "expected_outputs": {
            "balance_power_up": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            # power_down depends on optimization, validated in integration tests
        },
    },
    {
        "description": "Balance connection with capacity shrinkage",
        "factory": BatteryBalanceConnection,
        "data": {
            "name": "balance_shrink",
            "periods": [1.0] * 3,
            "upper": "normal_battery",
            "lower": "undercharge_battery",
            "capacity_lower": [5.0, 4.0, 3.0, 3.0],  # T+1 fence-posted, shrinking
        },
        "expected_outputs": {
            # power_up = capacity_shrinkage / period
            # shrinkage: [5-4, 4-3, 3-3] = [1, 1, 0]
            # power_up: [1/1, 1/1, 0/1] = [1.0, 1.0, 0.0]
            "balance_power_up": {"type": "power_flow", "unit": "kW", "values": (1.0, 1.0, 0.0)},
        },
    },
    {
        "description": "Balance connection with capacity growth",
        "factory": BatteryBalanceConnection,
        "data": {
            "name": "balance_grow",
            "periods": [1.0] * 3,
            "upper": "normal_battery",
            "lower": "undercharge_battery",
            "capacity_lower": [3.0, 4.0, 5.0, 5.0],  # T+1 fence-posted, growing
        },
        "expected_outputs": {
            # No capacity shrinkage, so power_up = 0
            "balance_power_up": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Balance connection with variable period durations",
        "factory": BatteryBalanceConnection,
        "data": {
            "name": "balance_variable_periods",
            "periods": [0.5, 1.0, 2.0],  # Variable period durations
            "upper": "normal_battery",
            "lower": "undercharge_battery",
            "capacity_lower": [5.0, 4.0, 3.0, 3.0],  # 1kWh shrinkage in first two periods
        },
        "expected_outputs": {
            # power_up = capacity_shrinkage / period
            # shrinkage: [1, 1, 0]
            # power_up: [1/0.5, 1/1.0, 0/2.0] = [2.0, 1.0, 0.0]
            "balance_power_up": {"type": "power_flow", "unit": "kW", "values": (2.0, 1.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ConnectionTestCase] = [
    # Note: Invalid cases would be validated during network.add() when batteries are not found
    # The BatteryBalanceConnection itself accepts any string for upper/lower
]
