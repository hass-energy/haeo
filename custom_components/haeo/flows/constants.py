"""Utilities for managing configurable sentinel entities in config flows."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN, HAEO_CONFIGURABLE, HAEO_CONFIGURABLE_ENTITY_ID


def ensure_configurable_entities_exist(hass: HomeAssistant) -> None:
    """Ensure the configurable sentinel entity exists for config flows.

    Creates a single configurable entity in the 'haeo' domain.
    This entity appears in all EntitySelector dropdowns because we include
    'haeo' in the domain filter list.

    Args:
        hass: Home Assistant instance.

    """
    registry = er.async_get(hass)

    # Register in entity registry (needed for EntitySelector to show it)
    existing_entry = registry.async_get(HAEO_CONFIGURABLE_ENTITY_ID)
    if existing_entry is None:
        registry.async_get_or_create(
            domain=DOMAIN,  # Use 'haeo' domain so entity_id is haeo.configurable_entity
            platform=DOMAIN,
            unique_id=HAEO_CONFIGURABLE,
            suggested_object_id=HAEO_CONFIGURABLE,
            original_name="HAEO Configurable",
            original_icon="mdi:tune",
        )

    # Also set the state (for any code that reads state values)
    hass.states.async_set(
        HAEO_CONFIGURABLE_ENTITY_ID,
        "configurable",
        {
            "friendly_name": "HAEO Configurable",
            "icon": "mdi:tune",
        },
    )
