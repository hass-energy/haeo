"""Entity platform setup for HAEO integration.

Provides a common setup function for sensor platform using a data-driven approach
based on coordinator outputs.
"""

from collections.abc import Callable
from enum import StrEnum, auto
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import ELEMENT_OUTPUT_NAMES

_LOGGER = logging.getLogger(__name__)


class ConfigEntityMode(StrEnum):
    """Operating mode for a config entity.

    Driven: User provided external entities in config flow. The entity
    displays the combined output from those entities with forecast attributes.
    The entity is read-only (changes are overwritten by coordinator updates).

    Editable: User provides input via the entity. The user's value is
    used for optimization, and forecast attributes are added while preserving
    the user's state value.
    """

    DRIVEN = auto()
    EDITABLE = auto()


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


__all__ = [
    "ConfigEntityMode",
    "EntityPlatform",
    "async_setup_platform_entities",
]
