"""Test data and factories for Connection element."""

import numpy as np

from custom_components.haeo.core.model.elements.connection import Connection

from .connection_types import ConnectionTestCase

VALID_CASES: list[ConnectionTestCase] = [
    {
        "description": "Connection with forward flow only",
        "factory": Connection,
        "data": {
            "name": "forward_connection",
            "periods": np.array([1.0] * 3),
            "source": "battery",
            "target": "load",
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 5.0}},
        },
        "inputs": {
            "maximize_power_out": True,
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (5.0, 5.0, 5.0)},
            "segments": {"power_limit": {"power_limit": {"type": "shadow_price", "unit": "$/kW", "values": (-1.0, -1.0, -1.0)}}},
        },
    },
    {
        "description": "Connection respecting forward power limit",
        "factory": Connection,
        "data": {
            "name": "limited_forward",
            "periods": np.array([1.0] * 2),
            "source": "gen",
            "target": "net",
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 4.0}},
        },
        "inputs": {
            "maximize_power_out": True,
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (4.0, 4.0)},
            "segments": {"power_limit": {"power_limit": {"type": "shadow_price", "unit": "$/kW", "values": (-1.0, -1.0)}}},
        },
    },
    {
        "description": "Connection with efficiency losses",
        "factory": Connection,
        "data": {
            "name": "inverter",
            "periods": np.array([1.0] * 2),
            "source": "dc",
            "target": "ac",
            "segments": {
                "efficiency": {"segment_type": "efficiency", "efficiency": 0.95},
                "power_limit": {"segment_type": "power_limit", "max_power": 10.0},
            },
        },
        "inputs": {
            "fix_power_in": [5.0, 5.0],
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (5.0, 5.0)},
        },
    },
    {
        "description": "Connection with transfer pricing and power flow",
        "factory": Connection,
        "data": {
            "name": "priced_active_link",
            "periods": np.array([1.0, 0.5]),
            "source": "cheap_grid",
            "target": "load_node",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 5.0},
                "pricing": {"segment_type": "pricing", "price": np.array([0.10, 0.20])},
            },
        },
        "inputs": {
            "maximize_power_out": True,
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (5.0, 5.0)},
            "segments": {"power_limit": {"power_limit": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.4)}}},
        },
    },
    {
        "description": "Connection with time-varying limits",
        "factory": Connection,
        "data": {
            "name": "varying_connection",
            "periods": np.array([1.0] * 3),
            "source": "grid",
            "target": "net",
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 5.0, 8.0])}},
        },
        "inputs": {
            "maximize_power_out": True,
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (10.0, 5.0, 8.0)},
            "segments": {"power_limit": {"power_limit": {"type": "shadow_price", "unit": "$/kW", "values": (-1.0, -1.0, -1.0)}}},
        },
    },
    {
        "description": "Connection with pricing cost minimization",
        "factory": Connection,
        "data": {
            "name": "priced_connection",
            "periods": np.array([1.0, 1.0]),
            "source": "node_a",
            "target": "node_b",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 4.0},
                "pricing": {"segment_type": "pricing", "price": np.array([0.10, 0.20])},
            },
        },
        "inputs": {
            "maximize_power_out": True,
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (4.0, 4.0)},
            "segments": {"power_limit": {"power_limit": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.8)}}},
        },
    },
    {
        "description": "Connection with fixed power",
        "factory": Connection,
        "data": {
            "name": "fixed_connection",
            "periods": np.array([1.0] * 2),
            "source": "generator",
            "target": "load",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 4.0, "fixed": True},
            },
        },
        "inputs": None,
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (4.0, 4.0)},
        },
    },
    {
        "description": "Connection with no segments passes through",
        "factory": Connection,
        "data": {
            "name": "passthrough",
            "periods": np.array([1.0] * 2),
            "source": "a",
            "target": "b",
        },
        "inputs": {
            "fix_power_in": [3.0, 7.0],
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (3.0, 7.0)},
        },
    },
    {
        "description": "Connection with efficiency and pricing chain",
        "factory": Connection,
        "data": {
            "name": "chain",
            "periods": np.array([1.0] * 2),
            "source": "dc",
            "target": "ac",
            "segments": {
                "efficiency": {"segment_type": "efficiency", "efficiency": 0.90},
                "power_limit": {"segment_type": "power_limit", "max_power": 10.0},
                "pricing": {"segment_type": "pricing", "price": np.array([0.10, 0.10])},
            },
        },
        "inputs": {
            "fix_power_in": [10.0, 10.0],
        },
        "expected_outputs": {
            "connection_power": {"type": "power_flow", "unit": "kW", "values": (10.0, 10.0)},
        },
    },
]

INVALID_CASES: list[ConnectionTestCase] = []
