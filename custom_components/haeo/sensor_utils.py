"""Utility functions for extracting and processing sensor data."""

from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


def get_output_sensors(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    """Get all output sensors created by this config entry.

    Returns a dict mapping entity_id to a cleaned sensor state dict.
    Uses State.as_dict() to get complete state information including:
    - entity_id, state, attributes, last_changed, last_updated, context

    Unstable fields that are removed:
    - friendly_name (can vary based on runtime conditions)
    - last_changed, last_updated, context (timestamp-based, not relevant for snapshot comparison)

    DateTime keys in nested dicts (e.g., forecast attributes) are converted to ISO
    strings for JSON compatibility.
    """
    entity_registry = er.async_get(hass)

    output_sensors: dict[str, dict[str, Any]] = {}

    # Get all entities created by this config entry
    for entity_entry in er.async_entries_for_config_entry(entity_registry, config_entry.entry_id):
        # Only include sensors from our domain
        if entity_entry.platform != DOMAIN:
            continue

        # Get the current state
        state = hass.states.get(entity_entry.entity_id)
        if state is None:
            continue

        # Get complete state as dict and create mutable copy
        state_dict = dict(state.as_dict())

        # Make attributes dict mutable and remove unstable fields
        if "attributes" in state_dict and isinstance(state_dict["attributes"], dict):
            state_dict["attributes"] = dict(state_dict["attributes"])
            state_dict["attributes"].pop("friendly_name", None)

        # Remove timestamp-based fields that aren't relevant for functional comparison
        state_dict.pop("last_changed", None)
        state_dict.pop("last_updated", None)
        state_dict.pop("last_reported", None)
        state_dict.pop("context", None)

        output_sensors[entity_entry.entity_id] = state_dict

    return output_sensors
