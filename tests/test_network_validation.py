"""Tests for network connectivity validation."""

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
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


@pytest.fixture
def mock_hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock hub config entry with tier configuration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Network",
            CONF_TIER_1_COUNT: 2,
            CONF_TIER_1_DURATION: 30,
            CONF_TIER_2_COUNT: 0,
            CONF_TIER_2_DURATION: 60,
            CONF_TIER_3_COUNT: 0,
            CONF_TIER_3_DURATION: 30,
            CONF_TIER_4_COUNT: 0,
            CONF_TIER_4_DURATION: 60,
        },
        entry_id="test_hub",
    )
    entry.add_to_hass(hass)
    return entry


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


async def test_validate_network_topology_empty(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Empty participant set is considered connected."""
    result = await validate_network_topology(hass, {}, mock_hub_entry)
    assert result.is_connected is True
    assert result.components == ()


async def test_validate_network_topology_with_implicit_connection(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Element with implicit connection field creates edge to target node."""
    # Set up mock sensors with forecast data
    hass.states.async_set(
        "sensor.import_price",
        "0.30",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.30}]},
    )
    hass.states.async_set(
        "sensor.export_price",
        "0.10",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.10}]},
    )

    participants: dict[str, ElementConfigSchema] = {
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
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
        },
    }

    result = await validate_network_topology(hass, participants, mock_hub_entry)

    assert result.is_connected is True
    assert result.components == (("grid", "main"),)


async def test_validate_network_topology_detects_disconnected(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Disconnected components are properly identified."""
    # Set up mock sensors with forecast data
    hass.states.async_set(
        "sensor.import_price",
        "0.30",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.30}]},
    )
    hass.states.async_set(
        "sensor.export_price",
        "0.10",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.10}]},
    )

    participants: dict[str, ElementConfigSchema] = {
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

    result = await validate_network_topology(hass, participants, mock_hub_entry)

    assert result.is_connected is False
    assert result.components == (("a", "grid_a"), ("b", "grid_b"))
    assert result.num_components == 2


async def test_validate_network_topology_with_battery(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Battery element works in validation with sensor data.

    Regression test for https://github.com/hass-energy/haeo/issues/109.
    Validation now loads actual sensor data with forecast_times from config entry.
    """
    # Set up mock sensors with present value (no forecast needed for constants)
    hass.states.async_set(
        "sensor.import_price",
        "0.30",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.30}]},
    )
    hass.states.async_set(
        "sensor.export_price",
        "0.10",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.10}]},
    )
    hass.states.async_set("sensor.battery_capacity", "10.0")
    hass.states.async_set("sensor.battery_soc", "50.0")
    hass.states.async_set("sensor.battery_min_soc", "10.0")
    hass.states.async_set("sensor.battery_max_soc", "90.0")
    hass.states.async_set("sensor.battery_efficiency", "95.0")

    participants: dict[str, ElementConfigSchema] = {
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
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
        },
        "battery": {
            CONF_ELEMENT_TYPE: "battery",
            CONF_NAME: "battery",
            BATTERY_CONF_CONNECTION: "main",
            CONF_CAPACITY: "sensor.battery_capacity",
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            CONF_MIN_CHARGE_PERCENTAGE: "sensor.battery_min_soc",
            CONF_MAX_CHARGE_PERCENTAGE: "sensor.battery_max_soc",
            CONF_EFFICIENCY: "sensor.battery_efficiency",
        },
    }

    result = await validate_network_topology(hass, participants, mock_hub_entry)

    assert result.is_connected is True
    # Battery creates internal elements: battery:normal, battery:node, and connections
    assert "battery:node" in str(result.components)
    assert "main" in str(result.components)


async def test_validate_network_topology_with_battery_all_sections(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Battery with undercharge/overcharge sections works in validation.

    Regression test for https://github.com/hass-energy/haeo/issues/109.
    Tests battery configuration with all optional SOC sections.
    """
    # Set up mock sensors with forecast data for price fields
    hass.states.async_set("sensor.battery_capacity", "10.0")
    hass.states.async_set("sensor.battery_soc", "50.0")
    hass.states.async_set(
        "sensor.undercharge_cost",
        "0.05",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.05}]},
    )
    hass.states.async_set(
        "sensor.overcharge_cost",
        "0.02",
        {"forecast": [{"start_time": "2025-01-01T00:00:00+00:00", "price": 0.02}]},
    )
    hass.states.async_set("sensor.battery_min_soc", "10.0")
    hass.states.async_set("sensor.battery_max_soc", "90.0")
    hass.states.async_set("sensor.battery_efficiency", "95.0")
    hass.states.async_set("sensor.battery_undercharge_pct", "5.0")
    hass.states.async_set("sensor.battery_overcharge_pct", "95.0")

    participants: dict[str, ElementConfigSchema] = {
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
            CONF_CAPACITY: "sensor.battery_capacity",
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            CONF_MIN_CHARGE_PERCENTAGE: "sensor.battery_min_soc",
            CONF_MAX_CHARGE_PERCENTAGE: "sensor.battery_max_soc",
            CONF_EFFICIENCY: "sensor.battery_efficiency",
            CONF_UNDERCHARGE_PERCENTAGE: "sensor.battery_undercharge_pct",
            CONF_OVERCHARGE_PERCENTAGE: "sensor.battery_overcharge_pct",
            CONF_UNDERCHARGE_COST: ["sensor.undercharge_cost"],
            CONF_OVERCHARGE_COST: ["sensor.overcharge_cost"],
        },
    }

    result = await validate_network_topology(hass, participants, mock_hub_entry)

    assert result.is_connected is True
    components_str = str(result.components)
    # All battery sections should be present in the topology
    assert "battery:undercharge" in components_str
    assert "battery:normal" in components_str
    assert "battery:overcharge" in components_str
    assert "battery:node" in components_str
