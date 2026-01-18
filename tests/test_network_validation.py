"""Tests for network connectivity validation."""

from typing import Any

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
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
)
from custom_components.haeo.elements.battery import CONF_CONNECTION as BATTERY_CONF_CONNECTION
from custom_components.haeo.elements.grid import CONF_CONNECTION as GRID_CONF_CONNECTION
from custom_components.haeo.elements.grid import CONF_EXPORT_PRICE, CONF_IMPORT_PRICE
from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE
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
    participants: dict[str, dict[str, Any]] = {
        "main_node": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "main",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "grid": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid",
            GRID_CONF_CONNECTION: "main",
            CONF_IMPORT_PRICE: [0.30, 0.30],
            CONF_EXPORT_PRICE: [0.10, 0.10],
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    assert result.components == (("grid", "main"),)


def test_validate_network_topology_detects_disconnected() -> None:
    """Disconnected components are properly identified."""
    participants: dict[str, dict[str, Any]] = {
        "node_a": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "a",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "node_b": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "b",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "grid_a": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid_a",
            GRID_CONF_CONNECTION: "a",
            CONF_IMPORT_PRICE: [0.30, 0.30],
            CONF_EXPORT_PRICE: [0.10, 0.10],
        },
        "grid_b": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid_b",
            GRID_CONF_CONNECTION: "b",
            CONF_IMPORT_PRICE: [0.30, 0.30],
            CONF_EXPORT_PRICE: [0.10, 0.10],
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is False
    assert result.components == (("a", "grid_a"), ("b", "grid_b"))
    assert result.num_components == 2


def test_validate_network_topology_with_battery() -> None:
    """Battery element works in validation with loaded config data."""
    participants: dict[str, dict[str, Any]] = {
        "main_node": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "main",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "grid": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid",
            GRID_CONF_CONNECTION: "main",
            CONF_IMPORT_PRICE: [0.30, 0.30],
            CONF_EXPORT_PRICE: [0.10, 0.10],
        },
        "battery": {
            CONF_ELEMENT_TYPE: "battery",
            CONF_NAME: "battery",
            BATTERY_CONF_CONNECTION: "main",
            CONF_CAPACITY: [10.0, 10.0, 10.0],
            CONF_INITIAL_CHARGE_PERCENTAGE: [50.0, 50.0],
            CONF_MAX_CHARGE_POWER: [5.0, 5.0],
            CONF_MAX_DISCHARGE_POWER: [5.0, 5.0],
            CONF_MIN_CHARGE_PERCENTAGE: [10.0, 10.0, 10.0],
            CONF_MAX_CHARGE_PERCENTAGE: [90.0, 90.0, 90.0],
            CONF_EFFICIENCY: [95.0, 95.0],
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    # Battery creates internal elements: battery:normal, battery:node, and connections
    assert "battery:node" in str(result.components)
    assert "main" in str(result.components)


def test_validate_network_topology_with_battery_all_sections() -> None:
    """Battery with undercharge/overcharge sections works in validation."""
    participants: dict[str, dict[str, Any]] = {
        "main_node": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "main",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "battery": {
            CONF_ELEMENT_TYPE: "battery",
            CONF_NAME: "battery",
            BATTERY_CONF_CONNECTION: "main",
            CONF_CAPACITY: [10.0, 10.0, 10.0],
            CONF_INITIAL_CHARGE_PERCENTAGE: [50.0, 50.0],
            CONF_MAX_CHARGE_POWER: [5.0, 5.0],
            CONF_MAX_DISCHARGE_POWER: [5.0, 5.0],
            CONF_MIN_CHARGE_PERCENTAGE: [10.0, 10.0, 10.0],
            CONF_MAX_CHARGE_PERCENTAGE: [90.0, 90.0, 90.0],
            CONF_EFFICIENCY: [95.0, 95.0],
            CONF_UNDERCHARGE_PERCENTAGE: [5.0, 5.0, 5.0],
            CONF_OVERCHARGE_PERCENTAGE: [95.0, 95.0, 95.0],
            CONF_UNDERCHARGE_COST: [0.05, 0.05],
            CONF_OVERCHARGE_COST: [0.02, 0.02],
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    components_str = str(result.components)
    # All battery sections should be present in the topology
    assert "battery:undercharge" in components_str
    assert "battery:normal" in components_str
    assert "battery:overcharge" in components_str
    assert "battery:node" in components_str
