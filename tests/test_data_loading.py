"""Tests for data loading module."""

from typing import cast

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data import load_element_configs, load_network
from custom_components.haeo.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
)
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET
from custom_components.haeo.elements.load import CONF_CONNECTION, CONF_FORECAST


async def test_load_network_successful_loads_load_participant(hass: HomeAssistant) -> None:
    """load_network should populate the network when all fields are available."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="loaded_entry")
    entry.add_to_hass(hass)

    # Set up test sensor
    hass.states.async_set("sensor.baseload", "2.5", {"unit_of_measurement": "kW"})

    participant_schemas = cast(
        "dict[str, ElementConfigSchema]",
        {
            "node": {
                CONF_ELEMENT_TYPE: "node",
                CONF_NAME: "main_bus",
            },
            "load": {
                CONF_ELEMENT_TYPE: "load",
                CONF_NAME: "Baseload",
                CONF_CONNECTION: "main_bus",
                CONF_FORECAST: ["sensor.baseload"],
            },
        },
    )

    forecast_times = [0, 1800, 3600, 5400, 7200]

    # Load configs first
    loaded_configs = await load_element_configs(
        hass,
        participant_schemas,
        forecast_times,
    )

    result = await load_network(
        entry,
        periods_seconds=[1800] * 4,
        participants=loaded_configs,
    )

    assert result.periods == [0.5] * 4  # 1800 seconds = 0.5 hours
    assert "Baseload" in result.elements


async def test_load_network_with_missing_sensors(hass: HomeAssistant) -> None:
    """Test load_element_configs raises ValueError when sensors are unavailable."""
    # Create a config with a sensor that doesn't exist
    participants = cast(
        "dict[str, ElementConfigSchema]",
        {
            "battery": {
                CONF_ELEMENT_TYPE: "battery",
                CONF_NAME: "battery",
                CONF_CAPACITY: "sensor.missing_battery_capacity",  # This sensor doesn't exist
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.missing_battery_soc",  # This sensor doesn't exist
                CONF_MIN_CHARGE_PERCENTAGE: 20.0,
                CONF_MAX_CHARGE_PERCENTAGE: 80.0,
                CONF_EFFICIENCY: 95.0,
            }
        },
    )

    forecast_times = [0, 1800, 3600]

    # Should raise ValueError because sensor is missing
    with pytest.raises(ValueError, match="No time series data available"):
        await load_element_configs(
            hass,
            participants,
            forecast_times,
        )


async def test_load_network_with_unavailable_sensor_state(hass: HomeAssistant) -> None:
    """Test load_network raises UpdateFailed when sensor state is unavailable."""
    # Create sensors with unavailable state
    hass.states.async_set("sensor.unavailable_capacity", "unavailable")
    hass.states.async_set("sensor.unavailable_soc", "unavailable")

    participants = cast(
        "dict[str, ElementConfigSchema]",
        {
            "battery": {
                CONF_ELEMENT_TYPE: "battery",
                CONF_NAME: "battery",
                CONF_CAPACITY: "sensor.unavailable_capacity",
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.unavailable_soc",
                CONF_MIN_CHARGE_PERCENTAGE: 20.0,
                CONF_MAX_CHARGE_PERCENTAGE: 80.0,
                CONF_EFFICIENCY: 95.0,
            }
        },
    )

    forecast_times = [0, 1800, 3600]

    # Should raise ValueError because sensor state is unavailable
    with pytest.raises(ValueError, match="No time series data available"):
        await load_element_configs(
            hass,
            participants,
            forecast_times,
        )


async def test_load_network_without_participants_raises(hass: HomeAssistant) -> None:
    """load_network should raise when no participants are provided."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="no_participants")
    entry.add_to_hass(hass)

    with pytest.raises(ValueError, match="No participants configured"):
        await load_network(
            entry,
            periods_seconds=[1800],
            participants={},
        )


async def test_load_network_sorts_connections_after_elements(hass: HomeAssistant) -> None:
    """Connections should be added after their source/target elements."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="sorted_connections")
    entry.add_to_hass(hass)

    participants = cast(
        "dict[str, ElementConfigData]",
        {
            "line": {
                CONF_ELEMENT_TYPE: "connection",
                CONF_NAME: "line",
                CONF_SOURCE: "node_a",
                CONF_TARGET: "node_b",
            },
            "node_a": {
                CONF_ELEMENT_TYPE: "node",
                CONF_NAME: "node_a",
            },
            "node_b": {
                CONF_ELEMENT_TYPE: "node",
                CONF_NAME: "node_b",
            },
        },
    )

    network = await load_network(
        entry,
        periods_seconds=[900],
        participants=participants,
    )

    # Nodes should be added before the connection even though the connection was listed first
    assert list(network.elements.keys()) == ["node_a", "node_b", "line"]


async def test_load_network_add_failure_is_wrapped(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Failures when adding model elements should be wrapped with ValueError."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="add_failure")
    entry.add_to_hass(hass)

    participants = cast(
        "dict[str, ElementConfigData]",
        {
            "node": {CONF_ELEMENT_TYPE: "node", CONF_NAME: "node"},
        },
    )

    # Force Network.add to raise
    def _raise(*_: object, **__: object) -> None:
        err = RuntimeError("boom")
        raise err

    monkeypatch.setattr("custom_components.haeo.data.Network.add", _raise)

    with pytest.raises(ValueError, match="Failed to add model element 'node'"):
        await load_network(
            entry,
            periods_seconds=[900],
            participants=participants,
        )
