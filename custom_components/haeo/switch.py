"""Switch platform for HAEO entities.

This platform is set up twice during integration setup:
1. INPUT_PLATFORMS (before coordinator): Creates input switches for element fields
2. OUTPUT_PLATFORMS (after coordinator): Creates auto-optimize control switch
"""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import CONF_ELEMENT_TYPE, ELEMENT_TYPE_NETWORK
from custom_components.haeo.elements import get_input_fields, is_element_config_schema
from custom_components.haeo.entities.device import get_or_create_element_device, get_or_create_network_device
from custom_components.haeo.entities.haeo_auto_optimize_switch import HaeoAutoOptimizeSwitch
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO switch entities from a config entry.

    This is called twice:
    1. Before coordinator: Creates input switches for boolean element fields
    2. After coordinator: Creates auto-optimize control switch
    """
    # Runtime data must be set by __init__.py before platforms are set up
    if config_entry.runtime_data is None:
        msg = "Runtime data not set - integration setup incomplete"
        raise RuntimeError(msg)

    runtime_data = config_entry.runtime_data
    coordinator = runtime_data.coordinator

    # Collect all entities to add
    entities: list[SwitchEntity] = []

    # If coordinator exists, this is the OUTPUT_PLATFORMS call - create auto-optimize switch
    if coordinator is not None:
        # Find network subentry for network device
        network_subentry = next(
            (s for s in config_entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK),
            None,
        )
        if network_subentry is not None:
            network_device_entry = get_or_create_network_device(hass, config_entry, network_subentry)
            auto_optimize_switch = HaeoAutoOptimizeSwitch(
                hass=hass,
                config_entry=config_entry,
                device_entry=network_device_entry,
                coordinator=coordinator,
            )
            entities.append(auto_optimize_switch)
            _LOGGER.debug("Created auto-optimize switch for network")
    else:
        # No coordinator yet - this is the INPUT_PLATFORMS call - create input switches
        horizon_manager = runtime_data.horizon_manager

        for subentry in config_entry.subentries.values():
            if not is_element_config_schema(subentry.data):
                continue
            element_config = subentry.data
            element_type = element_config[CONF_ELEMENT_TYPE]

            # Get input field definitions for this element type
            input_fields = get_input_fields(element_config)

            # Filter to only switch fields (by entity description class name)
            # Note: isinstance doesn't work due to Home Assistant's frozen_dataclass_compat wrapper
            switch_fields = [
                f for f in input_fields.values() if type(f.entity_description).__name__ == "SwitchEntityDescription"
            ]

            if not switch_fields:
                continue

            # Get or create device using centralized device creation
            # Input entities go on the main device (element_type matches device_name)
            device_entry = get_or_create_element_device(hass, config_entry, subentry, element_type)

            for field_info in switch_fields:
                # Only create entities for configured fields
                if field_info.field_name not in subentry.data:
                    continue

                entity = HaeoInputSwitch(
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
                _LOGGER.debug("Registered input entity: %s.%s", element_name, field_name)

    if entities:
        _LOGGER.debug("Creating %d switch entities for entry %s", len(entities), config_entry.entry_id)
        async_add_entities(entities)
    else:
        _LOGGER.debug("No switch entities to create for entry %s", config_entry.entry_id)
