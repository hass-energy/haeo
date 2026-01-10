"""Device registry helper for HAEO entities.

Provides a shared function for creating devices across all entity platforms,
ensuring consistent device identifiers, translation placeholders, and parent-child
relationships for sub-devices.
"""

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.haeo.const import DOMAIN


def get_or_create_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    subentry: ConfigSubentry,
    device_name: str | None = None,
) -> dr.DeviceEntry:
    """Get or create a device for an element subentry.

    Creates devices with consistent identifiers and translation placeholders.
    Sub-devices (where device_name differs from subentry_type) are linked to
    their parent device via the `via_device` parameter.

    When creating a sub-device, the parent device is created first if it doesn't
    exist, ensuring the parent-child relationship is properly established.

    Args:
        hass: Home Assistant instance.
        config_entry: The hub config entry.
        subentry: The element subentry.
        device_name: Device name for translation key. If None, uses subentry_type.
            For sub-devices (e.g., battery partitions), pass the specific device
            name like "battery_device_normal".

    Returns:
        The device entry for the element or sub-device.

    """
    device_registry = dr.async_get(hass)

    # Determine effective device name - defaults to element type
    effective_device_name = device_name if device_name is not None else subentry.subentry_type

    # Sub-devices have a different device_name than the element type
    is_sub_device = effective_device_name != subentry.subentry_type

    # Build translation placeholders from subentry data with name override
    # Subentry data values are converted to strings for translation
    translation_placeholders = {k: str(v) for k, v in subentry.data.items()}
    translation_placeholders["name"] = subentry.title

    # For sub-devices, ensure parent device exists and link via via_device
    via_device: tuple[str, str] | None = None
    if is_sub_device:
        parent_device_id = f"{config_entry.entry_id}_{subentry.subentry_id}"

        # Create parent device first if needed (using element type as translation key)
        device_registry.async_get_or_create(
            identifiers={(DOMAIN, parent_device_id)},
            config_entry_id=config_entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            translation_key=subentry.subentry_type,
            translation_placeholders=translation_placeholders,
        )

        via_device = (DOMAIN, parent_device_id)

    # Build identifier suffix - include device_name for sub-devices
    device_id_suffix = f"{subentry.subentry_id}_{effective_device_name}" if is_sub_device else subentry.subentry_id

    return device_registry.async_get_or_create(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")},
        config_entry_id=config_entry.entry_id,
        config_subentry_id=subentry.subentry_id,
        translation_key=effective_device_name,
        translation_placeholders=translation_placeholders,
        via_device=via_device,
    )


__all__ = ["get_or_create_device"]
