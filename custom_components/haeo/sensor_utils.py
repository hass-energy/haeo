"""Utility functions for extracting and processing sensor data."""

from typing import TypedDict, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


class ForecastItem(TypedDict):
    """Single forecast point in sensor attributes."""

    time: str  # ISO format after as_dict() serialization
    value: float | str  # Numeric or status string (e.g., "success")


class SensorAttributes(TypedDict, total=False):
    """Attributes dict for HAEO sensors.

    Uses total=False since not all attributes are always present.
    Other Home Assistant attributes pass through as additional keys.
    """

    unit_of_measurement: str | None
    forecast: list[ForecastItem]


class SensorStateDict(TypedDict):
    """Cleaned sensor state dict returned by get_output_sensors."""

    entity_id: str
    state: str
    attributes: SensorAttributes


def get_output_sensors(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, SensorStateDict]:
    """Get all output sensors created by this config entry.

    Returns a dict mapping entity_id to a cleaned sensor state dict.
    Uses State.as_dict() to get complete state information including:
    - entity_id, state, attributes, last_changed, last_updated, context

    Unstable fields that are removed:
    - last_changed, last_updated, context (timestamp-based, not relevant for snapshot comparison)

    Numeric values are preserved at full precision to ensure diagnostics are reproducible.
    """
    entity_registry = er.async_get(hass)

    output_sensors: dict[str, SensorStateDict] = {}

    # Collect sensor data
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

        # Cast to SensorStateDict after cleaning (state.as_dict() has extra fields we removed)
        output_sensors[entity_entry.entity_id] = cast("SensorStateDict", state_dict)

    return output_sensors
