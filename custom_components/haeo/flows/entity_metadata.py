"""Home Assistant entity metadata extraction."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.haeo.core.data.loader.extractors import EntityMetadata, extract


def extract_entity_metadata(hass: HomeAssistant) -> list[EntityMetadata]:
    """Extract metadata for all sensor and input_number entities.

    This should be called once and the result passed to schema_for_type to avoid
    repeated entity registry and state lookups.
    """
    entities: list[EntityMetadata] = []
    for state in hass.states.async_all():
        try:
            unit = extract(state).unit
        except (ValueError, KeyError, HomeAssistantError):
            unit = state.attributes.get("unit_of_measurement")

        entities.append(EntityMetadata(entity_id=state.entity_id, unit_of_measurement=unit))

    return entities
