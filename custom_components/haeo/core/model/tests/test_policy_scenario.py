"""Full tagged power flow scenario: Grid/Solar/Battery/Load.

System topology:
    Grid <-> Switchboard <-> Load
    Solar -> Switchboard
    Battery <-> Switchboard

Tag assignment (simulating compile_policies output):
    Tag 1 = Solar power (source_tag on solar node)
    Tag 2 = Battery power (source_tag on battery)
    Tag 3 = Grid power (source_tag on grid)

Per-tag pricing on connections:
    Solar -> Grid export: $0.02/kWh on tag 1
    Battery -> Grid export: $0.10/kWh on tag 2
    Battery -> Load: $0.01/kWh on tag 2

This tests the model layer's tag infrastructure directly, without
depending on the policy compilation adapter.
"""

from typing import Any, cast

import numpy as np
import pytest

from custom_components.haeo.core.model import ModelElementConfig
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.network import Network

# Tag assignments (simulating VLAN compilation output)
TAG_SOLAR = 1
TAG_BATTERY = 2
TAG_GRID = 3
ALL_TAGS = {TAG_SOLAR, TAG_BATTERY, TAG_GRID}


def _build_tagged_system(
    periods: np.ndarray,
    *,
    grid_import_price: np.ndarray,
    grid_export_price: np.ndarray,
    solar_max: np.ndarray,
    load_fixed: np.ndarray,
    battery_capacity: float = 5.0,
    battery_initial_kwh: float = 2.5,
    battery_max_power: float = 5.0,
) -> list[dict[str, Any]]:
    """Build model elements with pre-assigned tags."""
    n = len(periods)
    return [
        # Nodes with source tags and access lists
        {
            "element_type": "node",
            "name": "grid",
            "is_source": True,
            "is_sink": True,
            "source_tag": TAG_GRID,
            "access_list": list(ALL_TAGS),
        },
        {
            "element_type": "node",
            "name": "solar",
            "is_source": True,
            "is_sink": False,
            "source_tag": TAG_SOLAR,
        },
        {
            "element_type": "node",
            "name": "sw",
            "is_source": False,
            "is_sink": False,
            "access_list": list(ALL_TAGS),
        },
        {
            "element_type": "node",
            "name": "load",
            "is_source": False,
            "is_sink": True,
            "access_list": list(ALL_TAGS),
        },
        # Battery with source tag
        {
            "element_type": "battery",
            "name": "battery",
            "capacity": battery_capacity,
            "initial_charge": battery_initial_kwh,
            "source_tag": TAG_BATTERY,
            "access_list": list(ALL_TAGS),
        },
        # Grid -> Switchboard (import)
        {
            "element_type": "connection",
            "name": "grid_import",
            "source": "grid",
            "target": "sw",
            "tags": ALL_TAGS,
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.full(n, 100.0)},
                "pricing": {"segment_type": "pricing", "price": grid_import_price},
            },
        },
        # Switchboard -> Grid (export) with per-tag pricing
        {
            "element_type": "connection",
            "name": "grid_export",
            "source": "sw",
            "target": "grid",
            "tags": ALL_TAGS,
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.full(n, 100.0)},
                "pricing": {
                    "segment_type": "pricing",
                    "price": -grid_export_price,
                    "tag_costs": [
                        {"tag": TAG_SOLAR, "price": 0.02},
                        {"tag": TAG_BATTERY, "price": 0.10},
                    ],
                },
            },
        },
        # Solar -> Switchboard
        {
            "element_type": "connection",
            "name": "solar_conn",
            "source": "solar",
            "target": "sw",
            "tags": ALL_TAGS,
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": solar_max},
            },
        },
        # Battery -> Switchboard (discharge) with per-tag pricing
        {
            "element_type": "connection",
            "name": "battery_discharge",
            "source": "battery",
            "target": "sw",
            "tags": ALL_TAGS,
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.full(n, battery_max_power)},
                "pricing": {
                    "segment_type": "pricing",
                    "tag_costs": [{"tag": TAG_BATTERY, "price": 0.01}],
                },
            },
        },
        # Switchboard -> Battery (charge)
        {
            "element_type": "connection",
            "name": "battery_charge",
            "source": "sw",
            "target": "battery",
            "tags": ALL_TAGS,
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.full(n, battery_max_power)},
            },
        },
        # Switchboard -> Load
        {
            "element_type": "connection",
            "name": "load_conn",
            "source": "sw",
            "target": "load",
            "tags": ALL_TAGS,
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": load_fixed, "fixed": True},
            },
        },
    ]


def test_tagged_power_flow_scenario() -> None:
    """Model-level test: tagged power decomposition controls flows via per-tag pricing."""
    periods = np.ones(6)

    grid_import_price = np.array([0.30, 0.30, 0.005, 0.50, 0.50, 0.10])
    grid_export_price = np.array([0.04, 0.01, 0.005, 0.15, 0.05, 0.02])
    solar_max = np.array([5.0, 5.0, 0.0, 0.0, 0.0, 0.0])
    load_fixed = np.full(6, 2.0)

    elements = _build_tagged_system(
        periods,
        grid_import_price=grid_import_price,
        grid_export_price=grid_export_price,
        solar_max=solar_max,
        load_fixed=load_fixed,
        battery_capacity=10.0,
        battery_initial_kwh=0.0,
        battery_max_power=5.0,
    )

    network = Network(name="tagged_scenario", periods=periods)
    for elem in sorted(elements, key=lambda e: e.get("element_type") == "connection"):
        network.add(cast("ModelElementConfig", elem))

    cost = network.optimize()
    h = network._solver

    assert isinstance(cost, float)

    grid_imp = network.elements["grid_import"]
    grid_exp = network.elements["grid_export"]
    bat_dis = network.elements["battery_discharge"]

    assert isinstance(grid_imp, Connection)
    assert isinstance(grid_exp, Connection)
    assert isinstance(bat_dis, Connection)

    grid_import_flow = tuple(float(v) for v in h.vals(grid_imp.power_in))
    grid_export_flow = tuple(float(v) for v in h.vals(grid_exp.power_in))
    bat_discharge_flow = tuple(float(v) for v in h.vals(bat_dis.power_in))

    # Period 1: Solar surplus, cheap export ($0.01) + tag cost $0.02 = negative
    assert grid_export_flow[1] == pytest.approx(0.0, abs=0.1)

    # Period 2: Grid very cheap ($0.005), battery->load costs $0.01
    assert bat_discharge_flow[2] == pytest.approx(0.0, abs=0.1)
    assert grid_import_flow[2] > 1.0

    # Period 3: Grid expensive ($0.50), battery->load only $0.01
    assert bat_discharge_flow[3] > 1.0

    # Period 4: Grid expensive, battery has stored energy
    assert bat_discharge_flow[4] > 0.5
