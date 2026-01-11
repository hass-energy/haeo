"""Centralized device creation for HAEO entities.

This module provides a single source of truth for creating devices,
ensuring consistent device identifiers across all platforms (sensor, number, switch).
"""

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry

from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK

if TYPE_CHECKING:
    from custom_components.haeo.elements import ElementDeviceName


def get_or_create_element_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    subentry: ConfigSubentry,
    device_name: "ElementDeviceName",
) -> DeviceEntry:
    """Get or create a device for an element.

    Uses consistent identifier pattern (v0.1.0 compatible):
    {entry_id}_{subentry_id}_{device_name}

    This pattern is used for all devices including main devices and sub-devices.
    The device_name is always included in the identifier to maintain backwards
    compatibility with v0.1.0 configurations.

    Args:
        hass: Home Assistant instance
        config_entry: The config entry for the integration
        subentry: The subentry for the element
        device_name: The device name (from adapter outputs)

    Returns:
        The device entry for this element/sub-element

    """
    device_registry = dr.async_get(hass)

    # Always include device_name in identifier for v0.1.0 compatibility
    device_id_suffix = f"{subentry.subentry_id}_{device_name}"

    return device_registry.async_get_or_create(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")},
        config_entry_id=config_entry.entry_id,
        config_subentry_id=subentry.subentry_id,
        translation_key=device_name,
        translation_placeholders={"name": subentry.title},
    )


def get_or_create_network_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    network_subentry: ConfigSubentry,
) -> DeviceEntry:
    """Get or create the network device for optimization outputs.

    The network device uses a consistent identifier pattern (v0.1.0 compatible):
    {entry_id}_{subentry_id}_{network}

    Args:
        hass: Home Assistant instance
        config_entry: The config entry for the integration
        network_subentry: The network subentry

    Returns:
        The device entry for the network

    """
    device_registry = dr.async_get(hass)

    # Always include device type in identifier for v0.1.0 compatibility
    device_id_suffix = f"{network_subentry.subentry_id}_{ELEMENT_TYPE_NETWORK}"

    return device_registry.async_get_or_create(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")},
        config_entry_id=config_entry.entry_id,
        config_subentry_id=network_subentry.subentry_id,
        translation_key=ELEMENT_TYPE_NETWORK,
        translation_placeholders={"name": network_subentry.title},
    )


def build_device_identifier(
    config_entry: ConfigEntry,
    subentry: ConfigSubentry,
    device_name: str,
) -> tuple[str, str]:
    """Build a device identifier tuple for matching purposes.

    Uses consistent identifier pattern (v0.1.0 compatible):
    {entry_id}_{subentry_id}_{device_name}

    This is useful for async_remove_config_entry_device to check if a device
    belongs to a current element.

    Args:
        config_entry: The config entry for the integration
        subentry: The subentry for the element
        device_name: The device name (required)

    Returns:
        Identifier tuple (DOMAIN, identifier_string)

    """
    # Always include device_name in identifier for v0.1.0 compatibility
    device_id_suffix = f"{subentry.subentry_id}_{device_name}"

    return (DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")


__all__ = [
    "build_device_identifier",
    "get_or_create_element_device",
    "get_or_create_network_device",
]
