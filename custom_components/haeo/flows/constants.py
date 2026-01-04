"""Utilities for managing configurable sentinel entities in config flows."""

from homeassistant.core import async_get_hass
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN, HAEO_CONFIGURABLE_UNIQUE_ID


def ensure_configurable_entities_exist() -> None:
    """Ensure the configurable sentinel entity exists for config flows.

    Creates a single configurable entity in the 'haeo' domain.
    This entity appears in all EntitySelector dropdowns because we include
    'haeo' in the domain filter list.

    Uses async_get_hass() to retrieve the Home Assistant instance from the
    current context.
    """
    hass = async_get_hass()
    registry = er.async_get(hass)

    # Look up by unique_id (stable) rather than entity_id (user can rename)
    existing_entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, HAEO_CONFIGURABLE_UNIQUE_ID)
    if existing_entity_id is None:
        # Create the entity - suggested_object_id is just a hint, actual entity_id may differ
        entry = registry.async_get_or_create(
            domain=DOMAIN,  # Use 'haeo' domain so entity_id is haeo.configurable_entity
            platform=DOMAIN,
            unique_id=HAEO_CONFIGURABLE_UNIQUE_ID,
            suggested_object_id="configurable_entity",
            original_name="HAEO Configurable",
            original_icon="mdi:tune",
        )
        existing_entity_id = entry.entity_id

    # Also set the state using the actual entity_id (for any code that reads state values)
    hass.states.async_set(
        existing_entity_id,
        "configurable",
        {
            "friendly_name": "HAEO Configurable",
            "icon": "mdi:tune",
        },
    )
