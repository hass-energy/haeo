"""Tests for network connectivity validation."""

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import ElementConfigSchema
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
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
    participants: dict[str, ElementConfigSchema] = {
        "main": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "main",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "grid": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid",
            GRID_CONF_CONNECTION: "main",
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    assert result.components == (("grid", "main"),)


def test_validate_network_topology_detects_disconnected() -> None:
    """Disconnected components are properly identified."""
    participants: dict[str, ElementConfigSchema] = {
        "a": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "a",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "b": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "b",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "grid_a": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid_a",
            GRID_CONF_CONNECTION: "a",
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
        },
        "grid_b": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid_b",
            GRID_CONF_CONNECTION: "b",
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is False
    assert result.components == (("a", "grid_a"), ("b", "grid_b"))
    assert result.num_components == 2


def test_validate_network_topology_with_battery() -> None:
    """Battery element works in validation.

    Regression test for https://github.com/hass-energy/haeo/issues/109.
    Validation now works directly from schema data without loading sensors.
    """
    participants: dict[str, ElementConfigSchema] = {
        "main": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "main",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "grid": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid",
            GRID_CONF_CONNECTION: "main",
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
        },
        "battery": {
            CONF_ELEMENT_TYPE: "battery",
            CONF_NAME: "battery",
            BATTERY_CONF_CONNECTION: "main",
            CONF_CAPACITY: ["sensor.battery_capacity"],
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MIN_CHARGE_PERCENTAGE: 10.0,
            CONF_MAX_CHARGE_PERCENTAGE: 90.0,
            CONF_EFFICIENCY: 95.0,
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    # All elements connect via the 'main' node
    assert "battery" in str(result.components)
    assert "main" in str(result.components)


def test_validate_network_topology_with_battery_all_sections() -> None:
    """Battery with undercharge/overcharge sections works in validation.

    Regression test for https://github.com/hass-energy/haeo/issues/109.
    Tests battery configuration with all optional SOC sections.
    """
    participants: dict[str, ElementConfigSchema] = {
        "main": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "main",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "battery": {
            CONF_ELEMENT_TYPE: "battery",
            CONF_NAME: "battery",
            BATTERY_CONF_CONNECTION: "main",
            CONF_CAPACITY: ["sensor.battery_capacity"],
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MIN_CHARGE_PERCENTAGE: 10.0,
            CONF_MAX_CHARGE_PERCENTAGE: 90.0,
            CONF_EFFICIENCY: 95.0,
            CONF_UNDERCHARGE_PERCENTAGE: 5.0,
            CONF_OVERCHARGE_PERCENTAGE: 95.0,
            CONF_UNDERCHARGE_COST: ["sensor.undercharge_cost"],
            CONF_OVERCHARGE_COST: ["sensor.overcharge_cost"],
        },
    }

    result = validate_network_topology(participants)

    assert result.is_connected is True
    components_str = str(result.components)
    # Battery connects to main node
    assert "battery" in components_str
    assert "main" in components_str
