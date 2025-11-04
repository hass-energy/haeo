"""Network connectivity helpers for the HAEO integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .elements import ElementConfigSchema
from .repairs import create_disconnected_network_issue, dismiss_disconnected_network_issue
from .validation import collect_participant_configs, format_component_summary, validate_network_topology

_LOGGER = logging.getLogger(__name__)


def evaluate_network_connectivity(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    participant_configs: Mapping[str, ElementConfigSchema] | None = None,
) -> None:
    """Validate the network connectivity for an entry and manage repair issues."""

    participants = dict(participant_configs) if participant_configs is not None else collect_participant_configs(entry)
    result = validate_network_topology(participants)

    if result.is_connected:
        dismiss_disconnected_network_issue(hass, entry.entry_id)
        return

    create_disconnected_network_issue(hass, entry.entry_id, result.component_sets)

    summary = format_component_summary(result.components, separator=" | ")
    _LOGGER.warning(
        "Network %s has %d disconnected component(s): %s",
        entry.entry_id,
        result.num_components,
        summary or "no components",
    )


__all__ = ["evaluate_network_connectivity"]
