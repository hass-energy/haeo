"""Test data and factories for Connection element."""

import numpy as np

from custom_components.haeo.model.elements.connection import Connection

from .connection_types import ConnectionTestCase

VALID_CASES: list[ConnectionTestCase] = [
    {
        "description": "Connection with forward flow only",
        "factory": Connection,
        "data": {
            "name": "forward_connection",
            "periods": [1.0] * 3,
            "source": "battery",
            "target": "load",
            "segments": [{"segment_type": "power_limit", "max_power_st": np.array([5.0, 5.0, 5.0])}],
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
            "power_limit_power_limit_st": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
        },
    },
    {
        "description": "Connection with reverse flow only",
        "factory": Connection,
        "data": {
            "name": "reverse_connection",
            "periods": [1.0] * 3,
            "source": "grid",
            "target": "solar",
            "segments": [{"segment_type": "power_limit", "max_power_ts": np.array([3.0, 3.0, 3.0])}],
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
            "power_limit_power_limit_ts": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
            "connection_shadow_power_max_target_source": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
        },
    },
    {
        "description": "Connection respecting forward power limit",
        "factory": Connection,
        "data": {
            "name": "limited_forward",
            "periods": [1.0] * 2,
            "source": "gen",
            "target": "net",
            "segments": [{"segment_type": "power_limit", "max_power_st": np.array([4.0, 4.0])}],
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
            "power_limit_power_limit_st": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1)},
        },
    },
    {
        "description": "Connection with efficiency losses",
        "factory": Connection,
        "data": {
            "name": "inverter",
            "periods": [1.0] * 2,
            "source": "dc",
            "target": "ac",
            "segments": [
                {"segment_type": "efficiency", "efficiency_st": np.array([0.95, 0.95])},
                {"segment_type": "power_limit", "max_power_st": np.array([10.0, 10.0])},
            ],
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
            "power_limit_power_limit_st": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Connection with transfer pricing and power flow",
        "factory": Connection,
        "data": {
            "name": "priced_active_link",
            "periods": [1.0, 0.5],
            "source": "cheap_grid",
            "target": "load_node",
            "segments": [
                {"segment_type": "power_limit", "max_power_st": np.array([5.0, 5.0])},
                {"segment_type": "pricing", "price_st": np.array([0.10, 0.20])},  # Transfer pricing
            ],
        },
        "inputs": {
            "source_power": [None, None],  # Infinite source
            "target_power": [None, None],  # Infinite sink
            "source_cost": 0.0,
            "target_cost": -1.0,  # Strong incentive to consume at target
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (5.0, 5.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
            "power_limit_power_limit_st": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.4)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.4)},
        },
    },
    {
        "description": "Connection with time-varying limits",
        "factory": Connection,
        "data": {
            "name": "varying_connection",
            "periods": [1.0] * 3,
            "source": "grid",
            "target": "net",
            "segments": [{"segment_type": "power_limit", "max_power_st": np.array([10.0, 5.0, 8.0])}],
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
            "power_limit_power_limit_st": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)},
        },
    },
    {
        "description": "Connection with bidirectional transfer pricing and forward flow",
        "factory": Connection,
        "data": {
            "name": "bidirectional_priced",
            "periods": [1.0, 1.0],
            "source": "node_a",
            "target": "node_b",
            "segments": [
                {"segment_type": "power_limit", "max_power_st": np.array([4.0, 4.0]), "max_power_ts": np.array([3.0, 3.0])},
                {"segment_type": "pricing", "price_st": np.array([0.10, 0.20]), "price_ts": np.array([0.15, 0.25])},
            ],
        },
        "inputs": {
            "source_power": [None, None],
            "target_power": [None, None],
            "source_cost": 0.0,
            "target_cost": -1.0,  # Strong incentive to deliver power to target
        },
        "expected_outputs": {
            "connection_power_source_target": {"type": "power_flow", "unit": "kW", "values": (4.0, 4.0)},
            "connection_power_target_source": {"type": "power_flow", "unit": "kW", "values": (0.0, 0.0)},
            "power_limit_power_limit_st": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.8)},
            "power_limit_power_limit_ts": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "power_limit_time_slice": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.8)},
            "connection_shadow_power_max_target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_time_slice": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Connection with bidirectional efficiency losses",
        "factory": Connection,
        "data": {
            "name": "bidirectional_converter",
            "periods": [1.0] * 2,
            "source": "dc_bus",
            "target": "ac_bus",
            "segments": [
                {
                    "segment_type": "efficiency",
                    "efficiency_st": np.array([0.95, 0.95]),
                    "efficiency_ts": np.array([0.93, 0.93]),
                },
                {
                    "segment_type": "power_limit",
                    "max_power_st": np.array([10.0, 10.0]),
                    "max_power_ts": np.array([10.0, 10.0]),
                },
            ],
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
            "power_limit_power_limit_st": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "power_limit_power_limit_ts": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "power_limit_time_slice": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_source_target": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_time_slice": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Connection with fixed power in reverse direction",
        "factory": Connection,
        "data": {
            "name": "fixed_reverse",
            "periods": [1.0] * 2,
            "source": "load",
            "target": "generator",
            "segments": [{"segment_type": "power_limit", "max_power_ts": np.array([4.0, 4.0]), "fixed": True}],
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
            "power_limit_power_limit_ts": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
            "connection_shadow_power_max_target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ConnectionTestCase] = []
