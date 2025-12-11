"""Tests for data loading module."""

from typing import cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data import load_network
from custom_components.haeo.elements import ElementConfigSchema
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
)
from custom_components.haeo.elements.load import CONF_CONNECTION, CONF_FORECAST


async def test_load_network_successful_loads_load_participant(hass: HomeAssistant) -> None:
    """load_network should populate the network when all fields are available."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="loaded_entry")
    entry.add_to_hass(hass)

    # Set up test sensor
    hass.states.async_set("sensor.baseload", "2.5", {"unit_of_measurement": "kW"})

    participants = cast(
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

    result = await load_network(
        hass,
        entry,
        period_seconds=1800,
        n_periods=4,
        participants=participants,
        forecast_times=[0, 1800, 3600, 5400, 7200],
    )

    assert result.period == pytest.approx(0.5)
    assert "Baseload" in result.elements


async def test_load_network_with_missing_sensors(hass: HomeAssistant) -> None:
    """Test load_network raises UpdateFailed when sensors are unavailable."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")

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

    # Should raise UpdateFailed because sensor is missing
    with pytest.raises(UpdateFailed) as exc_info:
        await load_network(
            hass,
            entry,
            period_seconds=1800,
            n_periods=3,
            participants=participants,
            forecast_times=forecast_times,
        )

    assert exc_info.value.translation_key == "missing_sensors"
    placeholders = exc_info.value.translation_placeholders
    assert placeholders is not None
    assert "battery" in placeholders["unavailable_sensors"]


async def test_load_network_with_unavailable_sensor_state(hass: HomeAssistant) -> None:
    """Test load_network raises UpdateFailed when sensor state is unavailable."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")

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

    # Should raise UpdateFailed because sensor state is unavailable
    with pytest.raises(UpdateFailed) as exc_info:
        await load_network(
            hass,
            entry,
            period_seconds=1800,
            n_periods=3,
            participants=participants,
            forecast_times=forecast_times,
        )

    assert exc_info.value.translation_key == "missing_sensors"
    placeholders = exc_info.value.translation_placeholders
    assert placeholders is not None
    assert "battery" in placeholders["unavailable_sensors"]
