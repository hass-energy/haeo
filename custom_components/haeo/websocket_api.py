"""WebSocket API for HAEO React configuration UI.

This module provides custom websocket commands for the React frontend to:
- Get subentry data for reconfiguration
- Get participant names for connection dropdowns
- Get entity metadata for unit filtering
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import websocket_command
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from custom_components.haeo.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, ConnectivityLevel
from custom_components.haeo.elements import ELEMENT_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Set up the HAEO WebSocket API."""
    websocket_api.async_register_command(hass, websocket_get_subentry)
    websocket_api.async_register_command(hass, websocket_get_participants)
    websocket_api.async_register_command(hass, websocket_get_element_config)


@websocket_command(
    {
        vol.Required("type"): "haeo/get_subentry",
        vol.Required("entry_id"): str,
        vol.Required("subentry_id"): str,
    }
)
@callback
def websocket_get_subentry(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get subentry data for reconfiguration.

    Returns the subentry data including name, element type, and all config fields.
    """
    entry_id: str = msg["entry_id"]
    subentry_id: str = msg["subentry_id"]

    # Find the config entry
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        connection.send_error(msg["id"], "not_found", f"Config entry {entry_id} not found")
        return

    # Find the subentry
    subentry = entry.subentries.get(subentry_id)
    if subentry is None:
        connection.send_error(msg["id"], "not_found", f"Subentry {subentry_id} not found")
        return

    # Return the subentry data
    connection.send_result(
        msg["id"],
        {
            "subentry_id": subentry.subentry_id,
            "subentry_type": subentry.subentry_type,
            "title": subentry.title,
            "data": dict(subentry.data),
        },
    )


@websocket_command(
    {
        vol.Required("type"): "haeo/get_participants",
        vol.Required("entry_id"): str,
        vol.Optional("exclude_subentry_id"): str,
    }
)
@callback
def websocket_get_participants(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get available participant names for connection dropdowns.

    Returns element names that can be used as connection targets.
    Excludes the current subentry if specified.
    """
    entry_id: str = msg["entry_id"]
    exclude_id: str | None = msg.get("exclude_subentry_id")

    # Find the config entry
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        connection.send_error(msg["id"], "not_found", f"Config entry {entry_id} not found")
        return

    advanced_mode = entry.data.get(CONF_ADVANCED_MODE, False)
    participants: list[str] = []

    for subentry in entry.subentries.values():
        # Skip excluded subentry
        if subentry.subentry_id == exclude_id:
            continue

        element_type = subentry.data.get(CONF_ELEMENT_TYPE)
        if element_type not in ELEMENT_TYPES:
            continue

        connectivity = ELEMENT_TYPES[element_type].connectivity
        if connectivity == ConnectivityLevel.ALWAYS or (connectivity == ConnectivityLevel.ADVANCED and advanced_mode):
            participants.append(subentry.title)

    connection.send_result(msg["id"], {"participants": participants})


@websocket_command(
    {
        vol.Required("type"): "haeo/get_element_config",
        vol.Required("entry_id"): str,
    }
)
@callback
def websocket_get_element_config(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get configuration for all elements in a hub.

    Returns a list of all subentries with their element type, name, and data.
    Used by the React UI to populate connection dropdowns and show existing config.
    """
    entry_id: str = msg["entry_id"]

    # Find the config entry
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        connection.send_error(msg["id"], "not_found", f"Config entry {entry_id} not found")
        return

    elements: list[dict[str, Any]] = []
    for subentry in entry.subentries.values():
        element_type = subentry.data.get(CONF_ELEMENT_TYPE)
        elements.append(
            {
                "subentry_id": subentry.subentry_id,
                "subentry_type": subentry.subentry_type,
                "element_type": element_type,
                "name": subentry.title,
                "data": dict(subentry.data),
            }
        )

    connection.send_result(msg["id"], {"elements": elements})


__all__ = ["async_setup_websocket_api"]
