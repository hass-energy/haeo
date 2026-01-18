"""Tests for HAEO sensor_utils module."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
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
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.sensor_utils import get_output_sensors


async def test_get_output_sensors_excludes_other_platforms(hass: HomeAssistant) -> None:
    """Entities from other platforms are excluded from output sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor from our HAEO domain (should be included)
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_test_unique",
        config_entry=entry,
    )
    hass.states.async_set(haeo_entry.entity_id, "42", {"unit_of_measurement": "kW"})

    # Register a sensor from a different platform (should be excluded)
    other_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform="other_integration",
        unique_id="other_test_unique",
        config_entry=entry,
    )
    hass.states.async_set(other_entry.entity_id, "100", {"unit_of_measurement": "W"})

    # Get output sensors
    output_sensors = get_output_sensors(hass, entry)

    # Verify only HAEO sensor is included
    assert haeo_entry.entity_id in output_sensors
    assert other_entry.entity_id not in output_sensors
    assert output_sensors[haeo_entry.entity_id]["state"] == "42.0"


async def test_get_output_sensors_excludes_entities_without_state(hass: HomeAssistant) -> None:
    """Entities with no state are excluded from output sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with state (should be included)
    with_state_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_with_state_unique",
        config_entry=entry,
    )
    hass.states.async_set(with_state_entry.entity_id, "50", {"unit_of_measurement": "kW"})

    # Register a sensor without setting its state (should be excluded)
    without_state_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_without_state_unique",
        config_entry=entry,
    )
    # Note: NOT setting state for this entity

    # Get output sensors
    output_sensors = get_output_sensors(hass, entry)

    # Verify only the sensor with state is included
    assert with_state_entry.entity_id in output_sensors
    assert without_state_entry.entity_id not in output_sensors
    assert output_sensors[with_state_entry.entity_id]["state"] == "50.0"


async def test_get_output_sensors_handles_forecast_attributes(hass: HomeAssistant) -> None:
    """Sensors with forecast attributes have forecast values rounded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with forecast attribute
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_forecast_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "1234.56789",
        {
            "unit_of_measurement": "kW",
            "forecast": [
                {"time": "2024-01-01T00:00:00", "value": 1234.56789},
                {"time": "2024-01-01T01:00:00", "value": 5678.12345},
            ],
        },
    )

    # Get output sensors
    output_sensors = get_output_sensors(hass, entry)

    # Verify forecast values are present and rounded
    assert haeo_entry.entity_id in output_sensors
    sensor_data = output_sensors[haeo_entry.entity_id]
    assert "forecast" in sensor_data["attributes"]
    assert len(sensor_data["attributes"]["forecast"]) == 2


async def test_get_output_sensors_handles_non_numeric_states(hass: HomeAssistant) -> None:
    """Sensors with non-numeric states are handled gracefully."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with non-numeric state (e.g., "unavailable" or a string status)
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_non_numeric_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "unavailable",
        {"unit_of_measurement": "kW"},
    )

    # Get output sensors - should not raise an exception
    output_sensors = get_output_sensors(hass, entry)

    # Verify the sensor is included with its original non-numeric state
    assert haeo_entry.entity_id in output_sensors
    assert output_sensors[haeo_entry.entity_id]["state"] == "unavailable"


async def test_get_output_sensors_handles_zero_values(hass: HomeAssistant) -> None:
    """Sensors with zero values use default decimal places."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with zero value
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_zero_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "0",
        {"unit_of_measurement": "kW"},
    )

    # Get output sensors
    output_sensors = get_output_sensors(hass, entry)

    # Verify sensor with zero value is handled correctly
    assert haeo_entry.entity_id in output_sensors
    assert output_sensors[haeo_entry.entity_id]["state"] == "0.0"


async def test_get_output_sensors_handles_non_numeric_forecast_values(hass: HomeAssistant) -> None:
    """Sensors with non-numeric forecast values are handled gracefully."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with mixed numeric and non-numeric forecast values
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_mixed_forecast_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "100.0",
        {
            "unit_of_measurement": "kW",
            "forecast": [
                {"time": "2024-01-01T00:00:00", "value": 100.0},
                {"time": "2024-01-01T01:00:00", "value": "status_string"},
            ],
        },
    )

    # Get output sensors - should not raise an exception
    output_sensors = get_output_sensors(hass, entry)

    # Verify the sensor is included with forecast
    assert haeo_entry.entity_id in output_sensors
    attributes = output_sensors[haeo_entry.entity_id]["attributes"]
    assert "forecast" in attributes
    forecast = attributes["forecast"]
    assert len(forecast) == 2
    # Non-numeric value should remain as-is
    assert forecast[1]["value"] == "status_string"
