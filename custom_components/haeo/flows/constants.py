"""Utilities for managing configurable sentinel entities in config flows."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN, HAEO_CONFIGURABLE_UNIQUE_ID

_LOGGER = logging.getLogger(__name__)


def setup_configurable_entity(hass: HomeAssistant) -> None:
    """Set up the configurable sentinel entity for config flows.

    Creates a single configurable entity in the 'haeo' domain.
    This entity appears in EntitySelector dropdowns when the haeo domain
    is included in the filter, allowing users to indicate they want to
    enter a constant value instead of selecting an external entity.

    Args:
        hass: Home Assistant instance.

    """
    registry = er.async_get(hass)

    # Look up by unique_id (stable) rather than entity_id (user can rename)
    existing_entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, HAEO_CONFIGURABLE_UNIQUE_ID)
    if existing_entity_id is None:
        # Create the entity - suggested_object_id is just a hint, actual entity_id may differ
        entry = registry.async_get_or_create(
            domain=DOMAIN,
            platform=DOMAIN,
            unique_id=HAEO_CONFIGURABLE_UNIQUE_ID,
            suggested_object_id="configurable_entity",
            original_name="HAEO Configurable",
            original_icon="mdi:tune",
        )
        existing_entity_id = entry.entity_id

    # Set state so the entity appears in selectors
    hass.states.async_set(
        existing_entity_id,
        "configurable",
        {
            "friendly_name": "HAEO Configurable",
            "icon": "mdi:tune",
        },
    )


__all__ = ["setup_configurable_entity"]
