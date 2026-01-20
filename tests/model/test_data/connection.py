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
            "periods": np.array([1.0] * 3),
            "source": "battery",
            "target": "load",
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power_source_target": 5.0}},
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
            "segments": {"power_limit": {"source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)}}},
        },
    },
    {
        "description": "Connection with reverse flow only",
        "factory": Connection,
        "data": {
            "name": "reverse_connection",
            "periods": np.array([1.0] * 3),
            "source": "grid",
            "target": "solar",
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power_target_source": 3.0}},
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
            "segments": {"power_limit": {"target_source": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)}}},
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
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power_source_target": 4.0}},
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
            "segments": {"power_limit": {"source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1)}}},
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
                "efficiency": {
                    "segment_type": "efficiency",
                    "efficiency_source_target": 0.95,
                },
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": 10.0,
                },
            },
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
            "segments": {"power_limit": {"source_target": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)}}},
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
                "power_limit": {"segment_type": "power_limit", "max_power_source_target": 5.0},
                "pricing": {"segment_type": "pricing", "price_source_target": np.array([0.10, 0.20])},  # Transfer pricing
            },
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
            "segments": {"power_limit": {"source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.4)}}},
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
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([10.0, 5.0, 8.0])}},
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
            "segments": {"power_limit": {"source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.1, -0.1, -0.1)}}},
        },
    },
    {
        "description": "Connection with bidirectional transfer pricing and forward flow",
        "factory": Connection,
        "data": {
            "name": "bidirectional_priced",
            "periods": np.array([1.0, 1.0]),
            "source": "node_a",
            "target": "node_b",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": 4.0,
                    "max_power_target_source": 3.0,
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.10, 0.20]),
                    "price_target_source": np.array([0.15, 0.25]),
                },
            },
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
            "segments": {
                "power_limit": {
                    "source_target": {"type": "shadow_price", "unit": "$/kW", "values": (-0.9, -0.8)},
                    "target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
                    "time_slice": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
                }
            },
        },
    },
    {
        "description": "Connection with bidirectional efficiency losses",
        "factory": Connection,
        "data": {
            "name": "bidirectional_converter",
            "periods": np.array([1.0] * 2),
            "source": "dc_bus",
            "target": "ac_bus",
            "segments": {
                "efficiency": {
                    "segment_type": "efficiency",
                    "efficiency_source_target": 0.95,
                    "efficiency_target_source": 0.93,
                },
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": 10.0,
                    "max_power_target_source": 10.0,
                },
            },
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
            "segments": {
                "power_limit": {
                    "source_target": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
                    "target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
                    "time_slice": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
                }
            },
        },
    },
    {
        "description": "Connection with fixed power in reverse direction",
        "factory": Connection,
        "data": {
            "name": "fixed_reverse",
            "periods": np.array([1.0] * 2),
            "source": "load",
            "target": "generator",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_target_source": 4.0,
                    "fixed": True,
                }
            },
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
            "segments": {"power_limit": {"target_source": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)}}},
        },
    },
]

INVALID_CASES: list[ConnectionTestCase] = []
