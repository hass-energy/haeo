"""Home Assistant entity metadata extraction."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.core.data.loader.extractors import EntityMetadata, extract


def extract_entity_metadata(hass: HomeAssistant, hub_entry: ConfigEntry) -> list[EntityMetadata]:
    """Extract metadata for selectable entities, excluding this hub's own entities.

    Entities created by this hub's config entry (e.g. HAEO input number/switch
    entities) are excluded so an element cannot reference a value produced by the
    same hub, which would create a confusing feedback loop.

    This should be called once and the result passed to schema_for_type to avoid
    repeated entity registry and state lookups.
    """
    registry = er.async_get(hass)
    own_entity_ids = {
        entry.entity_id for entry in er.async_entries_for_config_entry(registry, hub_entry.entry_id)
    }

    entities: list[EntityMetadata] = []
    for state in hass.states.async_all():
        if state.entity_id in own_entity_ids:
            continue
        try:
            unit = extract(state).unit
        except (ValueError, KeyError, HomeAssistantError):
            unit = state.attributes.get("unit_of_measurement")

        entities.append(EntityMetadata(entity_id=state.entity_id, unit_of_measurement=unit))

    return entities
