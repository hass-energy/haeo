"""Utility functions for HAEO."""

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import set_nested_config_value
if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry


async def async_update_subentry_value(
    hass: HomeAssistant,
    entry: "HaeoConfigEntry",
    subentry: ConfigSubentry,
    field_name: str,
    value: Any,
) -> None:
    """Update a single field value in a subentry without triggering reload.

    This function sets a flag on runtime_data before updating the subentry,
    which signals async_update_listener to skip the full integration reload
    and just refresh the coordinator instead.

    Args:
        hass: Home Assistant instance.
        entry: The hub config entry.
        subentry: The subentry to update.
        field_name: Name of the field to update.
        value: New value for the field.

    """
    # Set flag to prevent reload
    runtime_data = entry.runtime_data
    if runtime_data is not None:
        runtime_data.value_update_in_progress = True

    # Update subentry data with new value
    new_data = dict(subentry.data)
    if not set_nested_config_value(new_data, field_name, value):
        new_data[field_name] = value

    try:
        hass.config_entries.async_update_subentry(
            entry,
            subentry,
            data=new_data,
        )
    finally:
        # Ensure flag is cleared even if update fails
        if runtime_data is not None:
            runtime_data.value_update_in_progress = False


__all__ = [
    "async_update_subentry_value",
]
