"""Home Assistant entity metadata extraction."""

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, is_element_type
from custom_components.haeo.core.data.loader.extractors import EntityMetadata, extract, state_unit_conversion


def extract_entity_metadata(hass: HomeAssistant, hub_entry: ConfigEntry) -> list[EntityMetadata]:
    """Extract metadata for selectable entities, excluding this hub's own entities.

    Entities created by this hub's config entry (e.g. HAEO input number/switch
    entities) are excluded so an element cannot reference a value produced by the
    same hub, which would create a confusing feedback loop. The sensors of
    elements that can take part in a buffer are kept with the roles their
    element can take, as they stand for the element rather than being read.

    Each entity's unit is the base unit its values convert to, so it can be
    compared with the unit an input field's values are in. An entity whose
    state is not a reading right now reports the base unit of its stated unit.

    This should be called once and the result passed to schema_for_type to avoid
    repeated entity registry and state lookups.
    """
    registry = er.async_get(hass)
    own_entities = er.async_entries_for_config_entry(registry, hub_entry.entry_id)
    own_entity_ids = {entry.entity_id for entry in own_entities}
    subentry_roles = {
        subentry.subentry_id: ELEMENT_TYPES[subentry.subentry_type].buffer_roles
        for subentry in hub_entry.subentries.values()
        if is_element_type(subentry.subentry_type)
    }
    element_roles = {
        entry.entity_id: frozenset(roles)
        for entry in own_entities
        if entry.domain == SENSOR_DOMAIN and (roles := subentry_roles.get(entry.config_subentry_id or ""))
    }

    entities: list[EntityMetadata] = []
    for state in hass.states.async_all():
        if state.entity_id in own_entity_ids and state.entity_id not in element_roles:
            continue
        try:
            unit = extract(state, time_zone=dt_util.get_default_time_zone()).unit
        except (ValueError, KeyError, HomeAssistantError):
            unit = state_unit_conversion(state)[1]

        state_class = state.attributes.get("state_class")
        entities.append(
            EntityMetadata(
                entity_id=state.entity_id,
                unit_of_measurement=unit,
                state_class=state_class if isinstance(state_class, str) else None,
                element_roles=element_roles.get(state.entity_id, frozenset()),
            )
        )

    return entities
