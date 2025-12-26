"""Switch platform for Home Assistant Energy Optimizer integration.

This module creates input switch entities from element configuration.
Input entities are created directly from subentry config, not from coordinator data.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.entities import HaeoInputSwitch, async_setup_input_entities
from custom_components.haeo.schema.input_fields import InputEntityType

# Switch entities don't poll - they update via state change events or user input
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO switch entities from element subentry config."""
    await async_setup_input_entities(
        hass,
        config_entry,
        async_add_entities,
        InputEntityType.SWITCH,
        HaeoInputSwitch,
    )


__all__ = ["async_setup_entry"]
