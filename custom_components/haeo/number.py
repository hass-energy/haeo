"""Number platform for HAEO input entities."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.elements import get_input_fields, is_element_type
from custom_components.haeo.entities.device import get_or_create_element_device
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

    # List of (entity, element_name, field_name) tuples for registration
    entities: list[tuple[HaeoInputNumber, str, str]] = []

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

        # Get or create device using centralized device creation
        # Input entities go on the main device (element_type matches device_name)
        device_entry = get_or_create_element_device(hass, config_entry, subentry, element_type)

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
            # Store entity with its key for registration after async_add_entities
            element_name = subentry.title
            field_name = field_info.field_name
            entities.append((entity, element_name, field_name))

    if entities:
        _LOGGER.debug("Creating %d number entities for HAEO inputs", len(entities))
        async_add_entities([entity for entity, _, _ in entities])

        # Register in runtime_data AFTER async_add_entities completes
        # This ensures entities are added to HA before coordinator tries to watch them
        for entity, element_name, field_name in entities:
            runtime_data.input_entities[(element_name, field_name)] = entity
    else:
        _LOGGER.debug("No number entities to create for entry %s", config_entry.entry_id)
