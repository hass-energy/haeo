"""Number platform for HAEO input entities."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements import get_input_fields, is_element_type
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

    runtime_data = config_entry.runtime_data
    horizon_manager = runtime_data.horizon_manager

    entities: list[HaeoInputNumber] = []
    dr = device_registry.async_get(hass)

    for subentry in config_entry.subentries.values():
        # Skip non-element subentries (e.g., network)
        element_type = subentry.subentry_type
        if not is_element_type(element_type):
            continue

        # Get input field definitions for this element type
        input_fields = get_input_fields(element_type)

        # Filter to only number fields (by entity description class name)
        # Note: isinstance doesn't work due to Home Assistant's frozen_dataclass_compat wrapper
        number_fields = [f for f in input_fields if type(f.entity_description).__name__ == "NumberEntityDescription"]

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
            # Only create entities for configured fields
            if field_info.field_name not in subentry.data:
                continue

            entity = HaeoInputNumber(
                hass=hass,
                config_entry=config_entry,
                subentry=subentry,
                field_info=field_info,
                device_entry=device_entry,
                horizon_manager=horizon_manager,
            )
            entities.append(entity)

            # Register in runtime_data for coordinator access
            element_name = subentry.title
            field_name = field_info.field_name
            runtime_data.input_entities[(element_name, field_name)] = entity

    if entities:
        _LOGGER.debug("Creating %d number entities for HAEO inputs", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.debug("No number entities to create for entry %s", config_entry.entry_id)
