"""Entity platform setup for HAEO integration.

Provides setup functions for entity platforms:
- async_setup_sensor_entities: Creates sensor entities from coordinator data
- async_setup_input_entities: Creates number/switch entities from subentry config
"""

from collections.abc import Callable
import logging
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.schema.input_fields import InputEntityType, get_input_fields

from .haeo_number import HaeoInputNumber
from .haeo_switch import HaeoInputSwitch

_LOGGER = logging.getLogger(__name__)


# Type variable for input entity types
TInputEntity = TypeVar("TInputEntity", HaeoInputNumber, HaeoInputSwitch)


async def async_setup_sensor_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry[HaeoDataUpdateCoordinator | None],
    async_add_entities: AddEntitiesCallback,
    entity_factory: Callable[..., Entity],
) -> None:
    """Set up HAEO sensor entities from coordinator data.

    Creates sensor entities for optimization outputs (OUTPUT_NAMES).
    """
    coordinator = config_entry.runtime_data
    if coordinator is None:
        _LOGGER.debug("No coordinator available, skipping sensor setup")
        return

    entities: list[Entity] = []
    dr = device_registry.async_get(hass)

    if not coordinator.data:
        _LOGGER.debug("No coordinator data available for sensor setup")
        return

    elements = coordinator.data["elements"]

    for subentry in config_entry.subentries.values():
        element_data = elements.get(subentry.title)
        subentry_devices = element_data["outputs"] if element_data else {}
        translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        for device_name, device_outputs in subentry_devices.items():
            is_sub_device = device_name != subentry.title
            device_id_suffix = (
                f"{subentry.subentry_id}_{device_name}"
                if is_sub_device
                else subentry.subentry_id
            )
            device_entry = dr.async_get_or_create(
                identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")},
                config_entry_id=config_entry.entry_id,
                config_subentry_id=subentry.subentry_id,
                translation_key=device_name,
                translation_placeholders=translation_placeholders,
            )

            for output_name, output_data in device_outputs.items():
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
                )
                entities.append(entity)

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Created %d sensor entities", len(entities))
    else:
        _LOGGER.debug("No sensor entities created for entry %s", config_entry.entry_id)


async def async_setup_input_entities[TInputEntity: (HaeoInputNumber, HaeoInputSwitch)](
    hass: HomeAssistant,
    config_entry: ConfigEntry[HaeoDataUpdateCoordinator | None],
    async_add_entities: AddEntitiesCallback,
    input_entity_type: InputEntityType,
    entity_class: type[TInputEntity],
) -> None:
    """Set up HAEO input entities from element subentry config.

    Creates input entities for runtime configuration from subentry data.

    Args:
        hass: Home Assistant instance
        config_entry: The config entry to set up entities for
        async_add_entities: Callback to add entities
        input_entity_type: Filter for NUMBER or SWITCH fields
        entity_class: Entity class to instantiate (HaeoInputNumber or HaeoInputSwitch)

    """
    coordinator = config_entry.runtime_data
    if coordinator is None:
        _LOGGER.debug(
            "No coordinator available, skipping %s setup", input_entity_type.value
        )
        return

    entities: list[TInputEntity] = []
    dr = device_registry.async_get(hass)

    for subentry in config_entry.subentries.values():
        element_type = subentry.subentry_type

        # Only process element subentries
        if element_type in ELEMENT_TYPES:
            # Get input fields for this element type
            input_fields = get_input_fields(element_type)
            translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

            # Calculate device_id: use subentry_id for main device, append element_type for sub-devices
            is_sub_device = element_type != subentry.title
            device_id = (
                f"{subentry.subentry_id}_{element_type}"
                if is_sub_device
                else subentry.subentry_id
            )

            # Register device with same pattern as sensors
            dr.async_get_or_create(
                identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id}")},
                config_entry_id=config_entry.entry_id,
                config_subentry_id=subentry.subentry_id,
                translation_key=element_type,
                translation_placeholders=translation_placeholders,
            )

            # Create entities for matching input fields that have values in config
            for field_info in input_fields:
                if (
                    field_info.entity_type == input_entity_type
                    and field_info.field_name in subentry.data
                ):
                    entity = entity_class(
                        hass=hass,
                        coordinator=coordinator,
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
    "HaeoInputNumber",
    "HaeoInputSwitch",
    "async_setup_input_entities",
    "async_setup_sensor_entities",
]
