"""Utilities for managing constant sentinel entities in config flows."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN, HAEO_CONSTANT, HAEO_CONSTANT_ENTITY_ID, HAEO_DEVICE_CLASS


def ensure_constant_entities_exist(hass: HomeAssistant) -> None:
    """Ensure the constant sentinel entity exists for config flows.

    Creates a single constant entity in the 'haeo' domain with a special device class.
    This entity appears in all EntitySelector dropdowns because we include
    'haeo' in both the domain and device_class filter lists.

    Args:
        hass: Home Assistant instance.

    """
    registry = er.async_get(hass)

    # Register in entity registry (needed for EntitySelector to show it)
    existing_entry = registry.async_get(HAEO_CONSTANT_ENTITY_ID)
    if existing_entry is None:
        registry.async_get_or_create(
            domain=DOMAIN,  # Use 'haeo' domain so entity_id is haeo.constant
            platform=DOMAIN,
            unique_id=HAEO_CONSTANT,
            suggested_object_id=HAEO_CONSTANT,
            original_name="HAEO Constant Value",
            # Note: original_device_class expects SensorDeviceClass enum, but we use
            # a custom string. This works because HA stores it as a string internally.
            original_device_class=HAEO_DEVICE_CLASS,  # type: ignore[arg-type]
        )

    # Also set the state (for any code that reads state values)
    hass.states.async_set(
        HAEO_CONSTANT_ENTITY_ID,
        "0",
        {
            "friendly_name": "HAEO Constant Value",
            "device_class": HAEO_DEVICE_CLASS,
            "unit_of_measurement": None,
        },
    )
