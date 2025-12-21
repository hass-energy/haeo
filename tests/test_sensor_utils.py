"""Tests for HAEO sensor_utils module."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_DURATION,
    CONF_TIER_1_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_4_DURATION,
    CONF_TIER_4_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_4_DURATION,
    DEFAULT_TIER_4_COUNT,
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
