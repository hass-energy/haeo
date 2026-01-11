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


def build_device_identifier(
    config_entry: ConfigEntry,
    subentry: ConfigSubentry,
    device_name: str,
) -> tuple[str, str]:
    """Build a device identifier tuple.

    Uses identifier pattern: {entry_id}_{subentry_id}_{device_name}

    Args:
        config_entry: The config entry for the integration
        subentry: The subentry for the element
        device_name: The device name

    Returns:
        Identifier tuple (DOMAIN, identifier_string)

    """
    return (DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}_{device_name}")


def get_or_create_element_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    subentry: ConfigSubentry,
    device_name: "ElementDeviceName",
) -> DeviceEntry:
    """Get or create a device for an element.

    Args:
        hass: Home Assistant instance
        config_entry: The config entry for the integration
        subentry: The subentry for the element
        device_name: The device name (from adapter outputs)

    Returns:
        The device entry for this element/sub-element

    """
    device_registry = dr.async_get(hass)

    return device_registry.async_get_or_create(
        identifiers={build_device_identifier(config_entry, subentry, device_name)},
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

    Args:
        hass: Home Assistant instance
        config_entry: The config entry for the integration
        network_subentry: The network subentry

    Returns:
        The device entry for the network

    """
    device_registry = dr.async_get(hass)

    return device_registry.async_get_or_create(
        identifiers={build_device_identifier(config_entry, network_subentry, ELEMENT_TYPE_NETWORK)},
        config_entry_id=config_entry.entry_id,
        config_subentry_id=network_subentry.subentry_id,
        translation_key=ELEMENT_TYPE_NETWORK,
        translation_placeholders={"name": network_subentry.title},
    )


__all__ = [
    "build_device_identifier",
    "get_or_create_element_device",
    "get_or_create_network_device",
]
