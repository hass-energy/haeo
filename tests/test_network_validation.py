"""Tests for network connectivity validation."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import ElementConfigSchema
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


async def test_validate_network_topology_empty(hass: HomeAssistant) -> None:
    """Empty participant set is considered connected."""
    result = await validate_network_topology(hass, {})
    assert result.is_connected is True
    assert result.components == ()


async def test_validate_network_topology_with_implicit_connection(hass: HomeAssistant) -> None:
    """Element with implicit connection field creates edge to target node."""
    participants: dict[str, ElementConfigSchema] = {
        "main_node": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "main",
        },
        "grid": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid",
            "connection": "main",
            "import_price": ["sensor.import_price"],
            "export_price": ["sensor.export_price"],
        },
    }

    result = await validate_network_topology(hass, participants)

    assert result.is_connected is True
    assert result.components == (("grid", "main"),)


async def test_validate_network_topology_detects_disconnected(hass: HomeAssistant) -> None:
    """Disconnected components are properly identified."""
    participants: dict[str, ElementConfigSchema] = {
        "node_a": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "a",
        },
        "node_b": {
            CONF_ELEMENT_TYPE: "node",
            CONF_NAME: "b",
        },
        "grid_a": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid_a",
            "connection": "a",
            "import_price": ["sensor.import_price"],
            "export_price": ["sensor.export_price"],
        },
        "grid_b": {
            CONF_ELEMENT_TYPE: "grid",
            CONF_NAME: "grid_b",
            "connection": "b",
            "import_price": ["sensor.import_price"],
            "export_price": ["sensor.export_price"],
        },
    }

    result = await validate_network_topology(hass, participants)

    assert result.is_connected is False
    assert result.components == (("a", "grid_a"), ("b", "grid_b"))
    assert result.num_components == 2
