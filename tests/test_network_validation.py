"""Tests for network connectivity validation."""

import numpy as np

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import ElementConfigData
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_COST,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    BatteryConfigData,
)
from custom_components.haeo.elements.battery import CONF_CONNECTION as BATTERY_CONF_CONNECTION
from custom_components.haeo.elements.grid import CONF_CONNECTION as GRID_CONF_CONNECTION
from custom_components.haeo.elements.grid import CONF_EXPORT_PRICE, CONF_IMPORT_PRICE, GridConfigData
from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, NodeConfigData
from custom_components.haeo.validation import format_component_summary, validate_network_topology


def test_format_component_summary() -> None:
    """Component summary formats components with numbering."""
    components = [("a", "b"), ("c",), ("d", "e", "f")]
    summary = format_component_summary(components)
    assert "1) a, b" in summary
    assert "2) c" in summary
    assert "3) d, e, f" in summary


def test_format_component_summary_custom_separator() -> None:
    """Component summary respects custom separator."""
    components = [("a", "b"), ("c",)]
    summary = format_component_summary(components, separator=" | ")
    assert summary == "1) a, b | 2) c"


def test_validate_network_topology_empty() -> None:
    """Empty participant set is considered connected."""
    result = validate_network_topology({})
    assert result.is_connected is True
    assert result.components == ()


def test_validate_network_topology_with_implicit_connection() -> None:
    """Element with implicit connection field creates edge to target node."""
    main_node: NodeConfigData = {
        CONF_ELEMENT_TYPE: "node",
        CONF_NAME: "main",
        CONF_IS_SOURCE: False,
        CONF_IS_SINK: False,
    }
    grid: GridConfigData = {
        CONF_ELEMENT_TYPE: "grid",
        CONF_NAME: "grid",
        GRID_CONF_CONNECTION: "main",
        CONF_IMPORT_PRICE: np.array([0.30, 0.30]),
        CONF_EXPORT_PRICE: np.array([0.10, 0.10]),
    }
    participants: dict[str, ElementConfigData] = {"main_node": main_node, "grid": grid}

    result = validate_network_topology(participants)

    assert result.is_connected is True
    assert result.components == (("grid", "main"),)


def test_validate_network_topology_detects_disconnected() -> None:
    """Disconnected components are properly identified."""
    node_a: NodeConfigData = {
        CONF_ELEMENT_TYPE: "node",
        CONF_NAME: "a",
        CONF_IS_SOURCE: False,
        CONF_IS_SINK: False,
    }
    node_b: NodeConfigData = {
        CONF_ELEMENT_TYPE: "node",
        CONF_NAME: "b",
        CONF_IS_SOURCE: False,
        CONF_IS_SINK: False,
    }
    grid_a: GridConfigData = {
        CONF_ELEMENT_TYPE: "grid",
        CONF_NAME: "grid_a",
        GRID_CONF_CONNECTION: "a",
        CONF_IMPORT_PRICE: np.array([0.30, 0.30]),
        CONF_EXPORT_PRICE: np.array([0.10, 0.10]),
    }
    grid_b: GridConfigData = {
        CONF_ELEMENT_TYPE: "grid",
        CONF_NAME: "grid_b",
        GRID_CONF_CONNECTION: "b",
        CONF_IMPORT_PRICE: np.array([0.30, 0.30]),
        CONF_EXPORT_PRICE: np.array([0.10, 0.10]),
    }
    participants: dict[str, ElementConfigData] = {
        "node_a": node_a,
        "node_b": node_b,
        "grid_a": grid_a,
        "grid_b": grid_b,
    }

    result = validate_network_topology(participants)

    assert result.is_connected is False
    assert result.components == (("a", "grid_a"), ("b", "grid_b"))
    assert result.num_components == 2


def test_validate_network_topology_with_battery() -> None:
    """Battery element works in validation with loaded config data."""
    main_node: NodeConfigData = {
        CONF_ELEMENT_TYPE: "node",
        CONF_NAME: "main",
        CONF_IS_SOURCE: False,
        CONF_IS_SINK: False,
    }
    grid: GridConfigData = {
        CONF_ELEMENT_TYPE: "grid",
        CONF_NAME: "grid",
        GRID_CONF_CONNECTION: "main",
        CONF_IMPORT_PRICE: np.array([0.30, 0.30]),
        CONF_EXPORT_PRICE: np.array([0.10, 0.10]),
    }
    battery: BatteryConfigData = {
        CONF_ELEMENT_TYPE: "battery",
        CONF_NAME: "battery",
        BATTERY_CONF_CONNECTION: "main",
        CONF_CAPACITY: np.array([10.0, 10.0, 10.0]),
        CONF_INITIAL_CHARGE_PERCENTAGE: np.array([50.0, 50.0]),
        CONF_MAX_CHARGE_POWER: np.array([5.0, 5.0]),
        CONF_MAX_DISCHARGE_POWER: np.array([5.0, 5.0]),
        CONF_MIN_CHARGE_PERCENTAGE: np.array([10.0, 10.0, 10.0]),
        CONF_MAX_CHARGE_PERCENTAGE: np.array([90.0, 90.0, 90.0]),
        CONF_EFFICIENCY: np.array([95.0, 95.0]),
    }
    participants: dict[str, ElementConfigData] = {
        "main_node": main_node,
        "grid": grid,
        "battery": battery,
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    components_str = str(result.components)
    assert "battery" in components_str
    assert "main" in components_str


def test_validate_network_topology_with_battery_all_sections() -> None:
    """Battery with undercharge/overcharge sections works in validation."""
    main_node: NodeConfigData = {
        CONF_ELEMENT_TYPE: "node",
        CONF_NAME: "main",
        CONF_IS_SOURCE: False,
        CONF_IS_SINK: False,
    }
    battery: BatteryConfigData = {
        CONF_ELEMENT_TYPE: "battery",
        CONF_NAME: "battery",
        BATTERY_CONF_CONNECTION: "main",
        CONF_CAPACITY: np.array([10.0, 10.0, 10.0]),
        CONF_INITIAL_CHARGE_PERCENTAGE: np.array([50.0, 50.0]),
        CONF_MAX_CHARGE_POWER: np.array([5.0, 5.0]),
        CONF_MAX_DISCHARGE_POWER: np.array([5.0, 5.0]),
        CONF_MIN_CHARGE_PERCENTAGE: np.array([10.0, 10.0, 10.0]),
        CONF_MAX_CHARGE_PERCENTAGE: np.array([90.0, 90.0, 90.0]),
        CONF_EFFICIENCY: np.array([95.0, 95.0]),
        CONF_UNDERCHARGE_PERCENTAGE: np.array([5.0, 5.0, 5.0]),
        CONF_OVERCHARGE_PERCENTAGE: np.array([95.0, 95.0, 95.0]),
        CONF_UNDERCHARGE_COST: np.array([0.05, 0.05]),
        CONF_OVERCHARGE_COST: np.array([0.02, 0.02]),
    }
    participants: dict[str, ElementConfigData] = {
        "main_node": main_node,
        "battery": battery,
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    components_str = str(result.components)
    assert "battery" in components_str
    assert "main" in components_str
