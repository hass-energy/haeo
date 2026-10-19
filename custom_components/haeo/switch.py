"""Switch platform for HAEO input entities."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.elements import (
    get_input_fields,
    get_list_input_fields,
    is_element_config_schema,
    iter_input_field_paths,
)
from custom_components.haeo.elements.input_fields import is_switch_field_info
from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch
from custom_components.haeo.entities.device import get_or_create_element_device, get_or_create_network_device
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch

_LOGGER = logging.getLogger(__name__)

# Switch entities are backed by InputStore state, not by external I/O, so unlimited parallel updates is safe
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HAEO switch entities from a config entry.

    Creates switch entities for each boolean input field in element subentries.
    These entities serve as configurable inputs for the optimization model.

    Also creates the auto-optimize switch for the network device.
    """
    # Runtime data must be set by __init__.py before platforms are set up
    if config_entry.runtime_data is None:
        msg = "Runtime data not set - integration setup incomplete"
        raise RuntimeError(msg)

    runtime_data = config_entry.runtime_data
    horizon_manager = runtime_data.horizon_manager

    # Create input switches for each element's boolean fields
    for subentry in config_entry.subentries.values():
        if not is_element_config_schema(subentry.data):
            continue
        element_config = subentry.data
        element_type = element_config[CONF_ELEMENT_TYPE]

        # Get input field definitions for this element type
        input_fields = get_input_fields(element_config)
        list_input_fields = get_list_input_fields(element_config)
        all_fields = {**input_fields, **list_input_fields}

        # Filter to only switch fields (by entity description class name)
        # Note: isinstance doesn't work due to Home Assistant's frozen_dataclass_compat wrapper
        switch_fields = [
            (field_path, field_info)
            for field_path, field_info in iter_input_field_paths(all_fields)
            if is_switch_field_info(field_info)
        ]

        if not switch_fields:
            continue

        # Get or create device using centralized device creation
        # Input entities go on the main device (element_type matches device_name)
        device_entry = get_or_create_element_device(hass, config_entry, subentry, element_type)

        entities: list[SwitchEntity] = []
        for field_path, field_info in switch_fields:
            # Only create entities for fields that have a prebuilt store
            # (none/disabled fields are skipped during store construction)
            store = runtime_data.input_stores.get((subentry.title, field_path))
            if store is None:
                continue

            entity = HaeoInputSwitch(
                config_entry=config_entry,
                subentry=subentry,
                field_info=field_info,
                field_path=field_path,
                device_entry=device_entry,
                horizon_manager=horizon_manager,
                store=store,
            )
            entities.append(entity)
            _LOGGER.debug("Created input switch: %s.%s", subentry.title, ".".join(field_path))

        # Linking entities to their subentry removes them along with it
        _LOGGER.debug("Creating %d switch entities for %s", len(entities), subentry.title)
        async_add_entities(entities, config_subentry_id=subentry.subentry_id)

    # Create auto-optimize switch for the network device
    network_subentry = next(s for s in config_entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK)

    network_device = get_or_create_network_device(hass, config_entry, network_subentry)
    auto_optimize_switch = AutoOptimizeSwitch(
        config_entry=config_entry,
        device_entry=network_device,
    )
    runtime_data.auto_optimize_switch = auto_optimize_switch
    async_add_entities([auto_optimize_switch], config_subentry_id=network_subentry.subentry_id)
    _LOGGER.debug("Created auto-optimize switch for network")
