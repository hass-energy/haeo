"""Utilities for managing configurable sentinel entities in config flows."""

from homeassistant.core import async_get_hass
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import translation

from custom_components.haeo.const import CONFIGURABLE_ENTITY_UNIQUE_ID, DOMAIN

TRANSLATION_KEY = "configurable_entity"
ICON = "mdi:tune"


async def async_setup_sentinel_entities() -> None:
    """Set up the sentinel entities for config flows.

    Uses the entity registry directly (no platform forwarding) to avoid
    domain/platform naming conflicts that occur when platform name matches
    integration domain.
    """
    hass = async_get_hass()
    registry = er.async_get(hass)

    # Load translated name
    translations = await translation.async_get_translations(hass, hass.config.language, "entity", {DOMAIN})
    friendly_name = translations[f"component.{DOMAIN}.entity.{DOMAIN}.{TRANSLATION_KEY}.name"]

    # Look up by unique_id (stable) rather than entity_id (user can rename)
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID)
    if entity_id is None:
        entry = registry.async_get_or_create(
            domain=DOMAIN,
            platform=DOMAIN,
            unique_id=CONFIGURABLE_ENTITY_UNIQUE_ID,
            original_name=friendly_name,
            original_icon=ICON,
        )
        entity_id = entry.entity_id

    hass.states.async_set(
        entity_id,
        "",
        {"friendly_name": friendly_name, "icon": ICON},
    )


def async_unload_sentinel_entities() -> None:
    """Unload the sentinel entities.

    Removes the state and entity registry entry for the sentinel entities.
    """
    hass = async_get_hass()
    registry = er.async_get(hass)

    # Look up by unique_id to get the current entity_id
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID)
    if entity_id is not None:
        # Remove the state
        hass.states.async_remove(entity_id)
        # Remove from entity registry
        registry.async_remove(entity_id)
