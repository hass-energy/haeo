"""Tests for reserve graph walk (island discovery + path efficiencies)."""

import numpy as np
import pytest

from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.model.reserve_graph import discover_island


def _build_basic_network() -> Network:
    """Build a basic Grid-SW-Load-Solar-Battery network."""
    periods = np.array([0.5] * 4)
    net = Network(name="test", periods=periods)
    net.add({"element_type": "node", "name": "Grid", "is_source": True, "is_sink": True})
    net.add({"element_type": "node", "name": "SW", "is_source": False, "is_sink": False})
    net.add({"element_type": "node", "name": "Load", "is_source": False, "is_sink": True})
    net.add({"element_type": "node", "name": "Solar", "is_source": True, "is_sink": False})
    net.add({"element_type": "battery", "name": "Bat", "capacity": 10.0, "initial_charge": 5.0})

    net.add(
        {
            "element_type": "connection",
            "name": "Grid:import",
            "source": "Grid",
            "target": "SW",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": [0.30] * 4}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Grid:export",
            "source": "SW",
            "target": "Grid",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": [-0.05] * 4}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Solar:conn",
            "source": "Solar",
            "target": "SW",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": [5] * 4}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Load:conn",
            "source": "SW",
            "target": "Load",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": [3] * 4, "fixed": True}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Bat:charge",
            "source": "SW",
            "target": "Bat",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.90}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Bat:discharge",
            "source": "Bat",
            "target": "SW",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.95}},
        }
    )
    return net


def test_discover_basic_island() -> None:
    """Basic island: Grid auto-excluded, finds battery, load, solar."""
    net = _build_basic_network()
    island = discover_island(net)

    assert island.battery_names == ["Bat"]
    assert island.load_names == ["Load"]
    assert island.gen_names == ["Solar"]


def test_auto_exclude_grid_node() -> None:
    """Grid node (is_source=True, is_sink=True) auto-excluded from island."""
    net = _build_basic_network()
    island = discover_island(net)

    # Grid should not appear in any category
    assert "Grid" not in island.battery_names
    assert "Grid" not in island.load_names
    assert "Grid" not in island.gen_names


def test_battery_to_load_efficiency() -> None:
    """Efficiency from battery to load = product of connection efficiencies."""
    net = _build_basic_network()
    island = discover_island(net)

    # Bat -> SW (0.95 efficiency) -> Load (no efficiency segment = 1.0)
    assert island.battery_to_load_efficiency["Bat"]["Load"] == pytest.approx(0.95, abs=0.01)
    assert island.battery_avg_efficiency["Bat"] == pytest.approx(0.95, abs=0.01)


def test_multi_hop_efficiency() -> None:
    """Multi-hop path: Bat -> Inverter node -> SW -> Load compounds efficiency."""
    periods = np.array([0.5] * 4)
    net = Network(name="test", periods=periods)

    net.add({"element_type": "node", "name": "Grid", "is_source": True, "is_sink": True})
    net.add({"element_type": "node", "name": "DC_Bus", "is_source": False, "is_sink": False})
    net.add({"element_type": "node", "name": "AC_Bus", "is_source": False, "is_sink": False})
    net.add({"element_type": "node", "name": "Load", "is_source": False, "is_sink": True})
    net.add({"element_type": "battery", "name": "Bat", "capacity": 10.0, "initial_charge": 5.0})

    # Grid -> AC_Bus
    net.add(
        {
            "element_type": "connection",
            "name": "Grid:import",
            "source": "Grid",
            "target": "AC_Bus",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": [0.30] * 4}},
        }
    )
    # Bat -> DC_Bus (95% battery discharge efficiency)
    net.add(
        {
            "element_type": "connection",
            "name": "Bat:discharge",
            "source": "Bat",
            "target": "DC_Bus",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.95}},
        }
    )
    # DC_Bus -> AC_Bus (97% inverter efficiency)
    net.add(
        {
            "element_type": "connection",
            "name": "Inverter:dc_ac",
            "source": "DC_Bus",
            "target": "AC_Bus",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.97}},
        }
    )
    # AC_Bus -> Load
    net.add(
        {
            "element_type": "connection",
            "name": "Load:conn",
            "source": "AC_Bus",
            "target": "Load",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": [3] * 4, "fixed": True}},
        }
    )

    island = discover_island(net)

    # Bat -> DC_Bus (0.95) -> AC_Bus (0.97) -> Load (1.0) = 0.9215
    assert island.battery_to_load_efficiency["Bat"]["Load"] == pytest.approx(0.95 * 0.97, abs=0.01)


def test_manual_exclude_sheddable_load() -> None:
    """Manually exclude a sheddable load from the island."""
    net = _build_basic_network()
    # Add a sheddable load
    net.add({"element_type": "node", "name": "SheddableLoad", "is_source": False, "is_sink": True})
    net.add(
        {
            "element_type": "connection",
            "name": "SheddableLoad:conn",
            "source": "SW",
            "target": "SheddableLoad",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": [1] * 4, "fixed": True}},
        }
    )

    # Without exclusion: both loads found
    island_all = discover_island(net)
    assert "Load" in island_all.load_names
    assert "SheddableLoad" in island_all.load_names

    # With exclusion: sheddable load excluded
    island_shed = discover_island(net, exclude_elements={"Grid", "SheddableLoad"})
    assert "Load" in island_shed.load_names
    assert "SheddableLoad" not in island_shed.load_names


def test_multiple_batteries() -> None:
    """Multiple batteries in the island, each with different efficiencies."""
    periods = np.array([0.5] * 4)
    net = Network(name="test", periods=periods)

    net.add({"element_type": "node", "name": "Grid", "is_source": True, "is_sink": True})
    net.add({"element_type": "node", "name": "SW", "is_source": False, "is_sink": False})
    net.add({"element_type": "node", "name": "Load", "is_source": False, "is_sink": True})
    net.add({"element_type": "battery", "name": "BatA", "capacity": 10.0, "initial_charge": 5.0})
    net.add({"element_type": "battery", "name": "BatB", "capacity": 5.0, "initial_charge": 3.0})

    net.add(
        {
            "element_type": "connection",
            "name": "Grid:import",
            "source": "Grid",
            "target": "SW",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": [0.30] * 4}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Load:conn",
            "source": "SW",
            "target": "Load",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": [3] * 4, "fixed": True}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "BatA:discharge",
            "source": "BatA",
            "target": "SW",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.95}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "BatB:discharge",
            "source": "BatB",
            "target": "SW",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.90}},
        }
    )

    island = discover_island(net)

    assert sorted(island.battery_names) == ["BatA", "BatB"]
    assert island.battery_to_load_efficiency["BatA"]["Load"] == pytest.approx(0.95, abs=0.01)
    assert island.battery_to_load_efficiency["BatB"]["Load"] == pytest.approx(0.90, abs=0.01)
    assert island.battery_avg_efficiency["BatA"] == pytest.approx(0.95, abs=0.01)
    assert island.battery_avg_efficiency["BatB"] == pytest.approx(0.90, abs=0.01)
