"""Utilities for managing configurable sentinel entities in config flows.

Sentinel entities are shared across all HAEO config entries and use reference
counting to ensure they are only cleaned up when the last entry is unloaded.
"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import translation

from custom_components.haeo.const import CONFIGURABLE_ENTITY_UNIQUE_ID, DOMAIN

TRANSLATION_KEY = "configurable_entity"
ICON = "mdi:tune"

# Reference count key stored in hass.data
_SENTINEL_REF_COUNT_KEY = f"{DOMAIN}_sentinel_ref_count"


def _get_ref_count(hass: HomeAssistant) -> int:
    """Get the current sentinel reference count."""
    return hass.data.get(_SENTINEL_REF_COUNT_KEY, 0)


def _set_ref_count(hass: HomeAssistant, count: int) -> None:
    """Set the sentinel reference count."""
    if count <= 0:
        hass.data.pop(_SENTINEL_REF_COUNT_KEY, None)
    else:
        hass.data[_SENTINEL_REF_COUNT_KEY] = count


async def async_setup_sentinel_entities(hass: HomeAssistant) -> None:
    """Set up the sentinel entities for config flows.

    Uses reference counting to support multiple HAEO config entries.
    The sentinel is created on first setup and kept alive until all entries
    are unloaded.

    Uses the entity registry directly (no platform forwarding) to avoid
    domain/platform naming conflicts that occur when platform name matches
    integration domain.
    """
    # Increment reference count
    ref_count = _get_ref_count(hass) + 1
    _set_ref_count(hass, ref_count)

    # Only create on first reference
    if ref_count > 1:
        return

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
            suggested_object_id="configurable_entity",
            original_name=friendly_name,
            original_icon=ICON,
        )
        entity_id = entry.entity_id

    hass.states.async_set(
        entity_id,
        "",
        {"friendly_name": friendly_name, "icon": ICON},
    )


def async_unload_sentinel_entities(hass: HomeAssistant) -> None:
    """Unload the sentinel entities.

    Uses reference counting - only removes the sentinel when the last
    HAEO config entry is unloaded.
    """
    # Decrement reference count
    ref_count = _get_ref_count(hass) - 1
    _set_ref_count(hass, ref_count)

    # Only clean up on last reference
    if ref_count > 0:
        return

    registry = er.async_get(hass)

    # Look up by unique_id to get the current entity_id
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID)
    if entity_id is not None:
        # Remove the state
        hass.states.async_remove(entity_id)
        # Remove from entity registry
        registry.async_remove(entity_id)
