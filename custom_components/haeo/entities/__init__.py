"""Entity platform setup for HAEO integration.

Provides common setup functions for entity platforms:
- Sensor entities: Created from coordinator data (optimization outputs)
- Input entities: Created from subentry config (number/switch for runtime configuration)
"""

from collections.abc import Callable
from enum import StrEnum
import logging
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import ELEMENT_OUTPUT_NAMES, ELEMENT_TYPES
from custom_components.haeo.schema.input_fields import InputEntityType, get_input_fields

from .haeo_number import HaeoInputNumber
from .haeo_switch import HaeoInputSwitch
from .mode import ConfigEntityMode

_LOGGER = logging.getLogger(__name__)

# Type variable for input entity types
TInputEntity = TypeVar("TInputEntity", HaeoInputNumber, HaeoInputSwitch)


class EntityPlatform(StrEnum):
    """Entity platform types."""

    SENSOR = "sensor"
    NUMBER = "number"
    SWITCH = "switch"


async def async_setup_platform_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    platform: EntityPlatform,
    entity_factory: Callable[..., Entity],
) -> None:
    """Set up HAEO entities for a platform using coordinator data.

    This is the shared setup logic for sensor platforms.
    It iterates coordinator.data and creates sensor entities for OUTPUT_NAMES.
    Number and switch entities are created by the inputs/ module from subentry config.
    """
    coordinator: HaeoDataUpdateCoordinator | None = getattr(config_entry, "runtime_data", None)
    if coordinator is None:
        _LOGGER.debug("No coordinator available, skipping %s setup", platform.value)
        return

    entities: list[Entity] = []
    dr = device_registry.async_get(hass)

    if not coordinator.data:
        _LOGGER.debug("No coordinator data available for %s setup", platform.value)
        return

    for subentry in config_entry.subentries.values():
        subentry_devices = coordinator.data.get(subentry.title, {})
        translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        for device_name, device_outputs in subentry_devices.items():
            is_sub_device = device_name != subentry.title
            device_id_suffix = f"{subentry.subentry_id}_{device_name}" if is_sub_device else subentry.subentry_id

            device_entry = dr.async_get_or_create(
                identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")},
                config_entry_id=config_entry.entry_id,
                config_subentry_id=subentry.subentry_id,
                translation_key=device_name,
                translation_placeholders=translation_placeholders,
            )

            for output_name, output_data in device_outputs.items():
                # Determine if this output should be handled by this platform
                should_handle = False

                if platform == EntityPlatform.SENSOR:
                    # Sensors handle OUTPUT_NAMES (optimization results)
                    should_handle = output_name in ELEMENT_OUTPUT_NAMES

                # Number and switch entities are now created by the inputs/ module
                # from subentry config, not from coordinator data

                if not should_handle:
                    continue

                unique_id = f"{config_entry.entry_id}_{device_id_suffix}_{output_name}"

                entity = entity_factory(
                    coordinator,
                    device_entry=device_entry,
                    subentry_key=subentry.title,
                    device_key=device_name,
                    element_title=subentry.title,
                    element_type=subentry.subentry_type,
                    output_name=output_name,
                    output_data=output_data,
                    unique_id=unique_id,
                    translation_placeholders=translation_placeholders,
                    entity_mode=None,  # Only sensors use this path now, they don't use entity_mode
                )
                entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Created %d %s entities", len(entities), platform.value)
    else:
        _LOGGER.debug("No %s entities created for entry %s", platform.value, config_entry.entry_id)


async def async_setup_input_entities[TInputEntity: (HaeoInputNumber, HaeoInputSwitch)](
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    input_entity_type: InputEntityType,
    entity_class: type[TInputEntity],
) -> None:
    """Set up HAEO input entities from element subentry config.

    This is the shared setup logic for number and switch platforms.
    It creates input entities for runtime configuration from subentry data.

    Args:
        hass: Home Assistant instance
        config_entry: The config entry to set up entities for
        async_add_entities: Callback to add entities
        input_entity_type: Filter for NUMBER or SWITCH fields
        entity_class: Entity class to instantiate (HaeoInputNumber or HaeoInputSwitch)

    """
    entities: list[TInputEntity] = []
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

        # Create entities for matching input fields
        for field_info in input_fields:
            if field_info.entity_type != input_entity_type:
                continue

            # Only create entity if field has a value in config
            if field_info.field_name not in subentry.data:
                continue

            entity = entity_class(
                hass=hass,
                config_entry=config_entry,
                subentry=subentry,
                field_info=field_info,
                device_id=device_id,
            )
            entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Created %d %s entities", len(entities), input_entity_type.value)
    else:
        _LOGGER.debug(
            "No %s entities created for entry %s",
            input_entity_type.value,
            config_entry.entry_id,
        )


__all__ = [
    "ConfigEntityMode",
    "EntityPlatform",
    "HaeoInputNumber",
    "HaeoInputSwitch",
    "async_setup_input_entities",
    "async_setup_platform_entities",
]
