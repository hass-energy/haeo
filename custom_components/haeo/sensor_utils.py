"""Utility functions for extracting and processing sensor data."""

import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

# Default decimal places for values without a unit
_DEFAULT_DECIMAL_PLACES = 4

# Target significant figures for rounding
_TARGET_SIG_FIGS = 4


def _get_decimal_places(max_abs_value: float) -> int:
    """Calculate decimal places needed for approximately 4 significant figures."""
    if max_abs_value == 0:
        return _DEFAULT_DECIMAL_PLACES

    magnitude = math.floor(math.log10(max_abs_value))
    return max(0, _TARGET_SIG_FIGS - (magnitude + 1))


def get_output_sensors(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    """Get all output sensors created by this config entry.

    Returns a dict mapping entity_id to a cleaned sensor state dict.
    Uses State.as_dict() to get complete state information including:
    - entity_id, state, attributes, last_changed, last_updated, context

    Unstable fields that are removed:
    - friendly_name (can vary based on runtime conditions)
    - last_changed, last_updated, context (timestamp-based, not relevant for snapshot comparison)

    Numeric values are rounded intelligently based on their unit's maximum absolute value
    to provide approximately 4 significant figures, reducing noise from floating-point precision.
    """
    entity_registry = er.async_get(hass)

    output_sensors: dict[str, dict[str, Any]] = {}
    unit_values: dict[str | None, list[float]] = {}  # Map unit -> list of numeric values

    # First pass: collect sensor data and gather all numeric values by unit
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

        # Remove timestamp-based fields that aren't relevant for functional comparison
        state_dict.pop("last_changed", None)
        state_dict.pop("last_updated", None)
        state_dict.pop("last_reported", None)
        state_dict.pop("context", None)

        output_sensors[entity_entry.entity_id] = state_dict

        # Collect numeric values for unit-based rounding
        unit = state_dict.get("attributes", {}).get("unit_of_measurement")
        if unit not in unit_values:
            unit_values[unit] = []

        # Add state value if numeric
        if isinstance(state_dict.get("state"), str):
            try:
                state_val = float(state_dict["state"])
                unit_values[unit].append(abs(state_val))
            except (ValueError, TypeError):
                pass  # Non-numeric state (e.g., "success")

        # Add forecast values if present
        forecast = state_dict.get("attributes", {}).get("forecast")
        if isinstance(forecast, list):
            for item in forecast:
                if isinstance(item, dict) and "value" in item:
                    try:
                        value = float(item["value"])
                        unit_values[unit].append(abs(value))
                    except (ValueError, TypeError):
                        pass

    # Calculate decimal places for each unit
    unit_decimal_places: dict[str | None, int] = {}
    for unit, values in unit_values.items():
        if values:
            max_abs_value = max(values)
            unit_decimal_places[unit] = _get_decimal_places(max_abs_value)
        else:
            unit_decimal_places[unit] = _DEFAULT_DECIMAL_PLACES

    # Second pass: apply rounding to all numeric values
    for entity_data in output_sensors.values():
        # Round the state if it's numeric
        if isinstance(entity_data.get("state"), str):
            unit = entity_data.get("attributes", {}).get("unit_of_measurement")
            decimal_places = unit_decimal_places.get(unit, _DEFAULT_DECIMAL_PLACES)
            try:
                state_val = float(entity_data["state"])
                rounded_val = round(state_val, decimal_places) + 0.0  # Makes -0.0 into 0.0
                entity_data["state"] = str(rounded_val)
            except (ValueError, TypeError):
                pass  # Non-numeric state, leave as is

        # Round forecast values if present
        if "attributes" in entity_data and isinstance(entity_data["attributes"], dict):
            forecast = entity_data["attributes"].get("forecast")
            if isinstance(forecast, list):
                unit = entity_data["attributes"].get("unit_of_measurement")
                decimal_places = unit_decimal_places.get(unit, _DEFAULT_DECIMAL_PLACES)
                for item in forecast:
                    if isinstance(item, dict) and "value" in item:
                        try:
                            value = float(item["value"])
                            item["value"] = round(value, decimal_places) + 0.0  # Makes -0.0 into 0.0
                        except (ValueError, TypeError):
                            pass

    return output_sensors
