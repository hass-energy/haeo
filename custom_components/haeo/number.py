"""Number platform for HAEO input entities."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements import ELEMENT_TYPES, get_input_fields
from custom_components.haeo.elements.input_fields import NumberInputFieldInfo
from custom_components.haeo.entities.haeo_number import HaeoInputNumber

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO number entities from a config entry.

    Creates number entities for each numeric input field in element subentries.
    These entities serve as configurable inputs for the optimization model.
    """
    # Runtime data must be set by __init__.py before platforms are set up
    if config_entry.runtime_data is None:
        msg = "Runtime data not set - integration setup incomplete"
        raise RuntimeError(msg)

    horizon_entity = config_entry.runtime_data.horizon_entity
    if horizon_entity is None:
        # No horizon entity means no network subentry was configured
        _LOGGER.debug("No horizon entity available, skipping number entity setup")
        return

    entities: list[HaeoInputNumber] = []
    dr = device_registry.async_get(hass)

    for subentry in config_entry.subentries.values():
        # Skip non-element subentries (e.g., network)
        if subentry.subentry_type not in ELEMENT_TYPES:
            continue

        # Get input field definitions for this element type
        input_fields = get_input_fields(subentry.subentry_type)

        # Filter to only number fields
        number_fields = [f for f in input_fields if isinstance(f, NumberInputFieldInfo)]

        if not number_fields:
            continue

        # Get or create device for this subentry
        # Use the same identifier pattern as sensors for consistency
        device_entry = dr.async_get_or_create(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
            config_entry_id=config_entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            translation_key=subentry.subentry_type,
            translation_placeholders={"name": subentry.title},
        )

        for field_info in number_fields:
            # Only create entity if field is present in config
            if field_info.field_name not in subentry.data:
                continue

            entities.append(
                HaeoInputNumber(
                    hass=hass,
                    config_entry=config_entry,
                    subentry=subentry,
                    field_info=field_info,
                    device_entry=device_entry,
                    horizon_entity=horizon_entity,
                )
            )

    if entities:
        _LOGGER.debug("Creating %d number entities for HAEO inputs", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.debug("No number entities to create for entry %s", config_entry.entry_id)
