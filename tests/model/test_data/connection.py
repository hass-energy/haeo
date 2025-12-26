"""Test data and factories for Connection element."""

from custom_components.haeo.model.power_connection import PowerConnection

from .connection_types import ConnectionTestCase

VALID_CASES: list[ConnectionTestCase] = [
    {
        "description": "Connection with forward flow only",
        "factory": PowerConnection,
        "data": {
            "name": "forward_connection",
            "periods": [1.0] * 3,
            "source": "battery",
            "target": "load",
            "max_power_source_target": 5.0,
        },
        "inputs": {
            "source_power": [None, None, None],  # Infinite source
            "target_power": [None, None, None],  # Infinite sink
            "source_cost": 0.1,  # Cost to provide power from source
            "target_cost": -0.2,  # Revenue for consuming at target
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (5.0, 5.0, 5.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
        },
    },
    {
        "description": "Connection with reverse flow only",
        "factory": PowerConnection,
        "data": {
            "name": "reverse_connection",
            "periods": [1.0] * 3,
            "source": "grid",
            "target": "solar",
            "max_power_target_source": 3.0,
        },
        "inputs": {
            "source_power": [None, None, None],  # Infinite
            "target_power": [None, None, None],  # Infinite
            "source_cost": 0.2,  # Benefit for consuming at source (encourages reverse flow)
            "target_cost": -0.1,  # Benefit for providing from target (encourages reverse flow)
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (3.0, 3.0, 3.0)},
            "connection_shadow_power_max_target_source": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
        },
    },
    {
        "description": "Connection respecting forward power limit",
        "factory": PowerConnection,
        "data": {
            "name": "limited_forward",
            "periods": [1.0] * 2,
            "source": "gen",
            "target": "net",
            "max_power_source_target": 4.0,
        },
        "inputs": {
            "source_power": [None, None],
            "target_power": [None, None],
            "source_cost": 0.0,
            "target_cost": -0.1,
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (4.0, 4.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1)},
        },
    },
    {
        "description": "Connection with efficiency losses",
        "factory": PowerConnection,
        "data": {
            "name": "inverter",
            "periods": [1.0] * 2,
            "source": "dc",
            "target": "ac",
            "max_power_source_target": 10.0,
            "efficiency_source_target": 95.0,
        },
        "inputs": {
            "source_power": [5.0, 5.0],  # Fixed source
            "target_power": [None, None],  # Infinite sink
            "source_cost": 0.0,
            "target_cost": 0.0,
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (5.0, 5.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Connection with transfer pricing discouraging flow",
        "factory": PowerConnection,
        "data": {
            "name": "priced_link",
            "periods": [1.0] * 2,
            "source": "node_a",
            "target": "node_b",
            "price_source_target": [0.5, 0.5],  # High transfer cost
        },
        "inputs": {
            "source_power": [None, None],
            "target_power": [None, None],
            "source_cost": 0.1,
            "target_cost": -0.2,  # Not enough to offset transfer cost
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Connection with time-varying limits",
        "factory": PowerConnection,
        "data": {
            "name": "varying_connection",
            "periods": [1.0] * 3,
            "source": "grid",
            "target": "net",
            "max_power_source_target": [10.0, 5.0, 8.0],
        },
        "inputs": {
            "source_power": [None, None, None],
            "target_power": [None, None, None],
            "source_cost": 0.0,
            "target_cost": -0.1,
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (10.0, 5.0, 8.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
        },
    },
    {
        "description": "Connection with bidirectional transfer pricing",
        "factory": PowerConnection,
        "data": {
            "name": "bidirectional_priced",
            "periods": [1.0] * 2,
            "source": "node_a",
            "target": "node_b",
            "price_source_target": [0.1, 0.1],
            "price_target_source": [0.15, 0.15],
        },
        "inputs": {
            "source_power": [None, None],
            "target_power": [None, None],
            "source_cost": 0.0,
            "target_cost": 0.0,
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Connection with bidirectional efficiency losses",
        "factory": PowerConnection,
        "data": {
            "name": "bidirectional_converter",
            "periods": [1.0] * 2,
            "source": "dc_bus",
            "target": "ac_bus",
            "max_power_source_target": 10.0,
            "max_power_target_source": 10.0,
            "efficiency_source_target": 95.0,
            "efficiency_target_source": 93.0,
        },
        "inputs": {
            "source_power": [5.0, -3.0],
            "target_power": [None, None],
            "source_cost": 0.0,
            "target_cost": 0.0,
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (5.0, 0.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 3.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_time_slice": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Connection with fixed power in reverse direction",
        "factory": PowerConnection,
        "data": {
            "name": "fixed_reverse",
            "periods": [1.0] * 2,
            "source": "load",
            "target": "generator",
            "max_power_target_source": 4.0,
            "fixed_power": True,
        },
        "inputs": {
            "source_power": [None, None],
            "target_power": [None, None],
            "source_cost": 0.0,
            "target_cost": 0.0,
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (4.0, 4.0)},
            "connection_shadow_power_max_target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ConnectionTestCase] = []
