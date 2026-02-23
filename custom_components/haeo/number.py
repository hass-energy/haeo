"""Number platform for HAEO input entities."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import is_none_value
from custom_components.haeo.elements import (
    get_input_fields,
    get_nested_config_value_by_path,
    is_element_config_schema,
    iter_input_field_paths,
)
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

    entities: list[HaeoInputNumber] = []

    for subentry in config_entry.subentries.values():
        if not is_element_config_schema(subentry.data):
            continue
        element_config = subentry.data
        element_type = element_config[CONF_ELEMENT_TYPE]

        # Get input field definitions for this element type
        input_fields = get_input_fields(element_config)

        # Filter to only number fields (by entity description class name)
        # Note: isinstance doesn't work due to Home Assistant's frozen_dataclass_compat wrapper
        number_fields = [
            (field_path, field_info)
            for field_path, field_info in iter_input_field_paths(input_fields)
            if type(field_info.entity_description).__name__ == "NumberEntityDescription"
        ]

        if not number_fields:
            continue

        # Get or create device using centralized device creation
        # Input entities go on the main device (element_type matches device_name)
        device_entry = get_or_create_element_device(hass, config_entry, subentry, element_type)

        for field_path, field_info in number_fields:
            # Only create entities for configured fields
            config_value = get_nested_config_value_by_path(subentry.data, field_path)
            if config_value is None or is_none_value(config_value):
                continue

            entity = HaeoInputNumber(
                config_entry=config_entry,
                subentry=subentry,
                field_info=field_info,
                field_path=field_path,
                device_entry=device_entry,
                horizon_manager=horizon_manager,
            )
            entities.append(entity)

            # Register in runtime_data for coordinator access
            element_name = subentry.title
            runtime_data.input_entities[(element_name, field_path)] = entity

    if entities:
        _LOGGER.debug("Creating %d number entities for HAEO inputs", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.debug("No number entities to create for entry %s", config_entry.entry_id)
