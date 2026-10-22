"""Network connectivity checks for the HAEO integration."""

from collections.abc import Mapping
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.core.schema.elements import ElementConfigData
from custom_components.haeo.repairs import (
    create_disconnected_network_issue,
    create_invalid_connection_endpoints_issue,
    dismiss_disconnected_network_issue,
    dismiss_invalid_connection_endpoints_issue,
)
from custom_components.haeo.validation import (
    find_invalid_connection_endpoints,
    format_component_summary,
    validate_network_topology,
)

_LOGGER = logging.getLogger(__name__)


def evaluate_network_connectivity(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    participants: Mapping[str, ElementConfigData],
) -> None:
    """Validate the network connectivity for an entry and manage repair issues."""
    invalid_endpoints = find_invalid_connection_endpoints(participants)
    if invalid_endpoints:
        create_invalid_connection_endpoints_issue(hass, entry.entry_id, invalid_endpoints)
    else:
        dismiss_invalid_connection_endpoints_issue(hass, entry.entry_id)

    result = validate_network_topology(participants)

    if result.is_connected:
        dismiss_disconnected_network_issue(hass, entry.entry_id)
        return

    create_disconnected_network_issue(hass, entry.entry_id, result.components)

    summary = format_component_summary(result.components, separator=" | ")
    _LOGGER.warning(
        "Network %s has %d disconnected component(s): %s",
        entry.entry_id,
        result.num_components,
        summary or "no components",
    )


__all__ = ["evaluate_network_connectivity"]
