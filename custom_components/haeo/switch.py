"""Switch platform for Home Assistant Energy Optimizer integration.

This module creates input switch entities from element configuration.
Input entities are created directly from subentry config, not from coordinator data.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.inputs import HaeoInputSwitch
from custom_components.haeo.schema.input_fields import InputEntityType, get_input_fields

_LOGGER = logging.getLogger(__name__)

# Switch entities don't poll - they update via state change events or user input
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO switch entities from element subentry config."""
    entities: list[HaeoInputSwitch] = []
    dr = device_registry.async_get(hass)

    for subentry in config_entry.subentries.values():
        element_type = subentry.subentry_type

        # Skip non-element subentries
        if element_type not in ELEMENT_TYPES:
            continue

        # Get input fields for this element type
        input_fields = get_input_fields(element_type)

        # Get or create device for this element
        device_id = subentry.subentry_id
        translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        dr.async_get_or_create(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id}")},
            config_entry_id=config_entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            translation_key=element_type,
            translation_placeholders=translation_placeholders,
        )

        # Create switch entities for boolean input fields
        for field_info in input_fields:
            if field_info.entity_type != InputEntityType.SWITCH:
                continue

            # Only create entity if field has a value in config
            if field_info.field_name not in subentry.data:
                continue

            entity = HaeoInputSwitch(
                hass=hass,
                config_entry=config_entry,
                subentry=subentry,
                field_info=field_info,
                device_id=device_id,
            )
            entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Created %d input switch entities", len(entities))
    else:
        _LOGGER.debug("No input switch entities created for entry %s", config_entry.entry_id)


__all__ = ["async_setup_entry"]
