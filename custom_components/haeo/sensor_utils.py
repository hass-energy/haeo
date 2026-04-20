"""Utility functions for extracting and processing sensor data."""

import math
from typing import Any, TypedDict, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, ELEMENT_TYPE_NETWORK, OUTPUT_NAME_HORIZON, OUTPUT_NAME_OPTIMIZATION_DURATION
from .entities.device import build_device_identifier

# Default decimal places for values without a unit
_DEFAULT_DECIMAL_PLACES = 4

# Target significant figures for rounding.
# Using 3 sig figs ensures cross-platform LP solver degeneracy (different optimal
# vertices with the same cost) rounds to the same value on all architectures.
_TARGET_SIG_FIGS = 3


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


def _get_decimal_places(max_abs_value: float) -> int:
    """Calculate decimal places needed for approximately 4 significant figures."""
    if max_abs_value == 0:
        return _DEFAULT_DECIMAL_PLACES

    magnitude = math.floor(math.log10(max_abs_value))
    return max(0, _TARGET_SIG_FIGS - (magnitude + 1))


def _try_parse_float(value: Any) -> float | None:
    """Try to parse a value as float, returning None if not possible."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _apply_smart_rounding(output_sensors: dict[str, SensorStateDict]) -> None:
    """Apply intelligent rounding to numeric values in output sensors.

    Rounds each entity's numeric values (state + forecast) to approximately
    3 significant figures based on *that entity's* own maximum absolute value.
    This reduces noise from floating-point precision while preserving precision
    for entities whose values are orders of magnitude smaller than other entities.

    Rationale: grouping by unit (or any cross-entity scope) forces all values in
    the group to the coarsest precision of the largest-magnitude entity. That
    obliterates real signal in small-magnitude entities (e.g. a $10/kWh policy
    price reducing Amber sub-dollar prices to a single decimal place). LP solver
    degeneracy only affects values within a single entity's own magnitude, so
    per-entity rounding is sufficient for cross-platform scenario stability.

    Modifies output_sensors in place by rounding:
    - State values (if numeric strings)
    - Forecast values in attributes (if present and numeric)

    Args:
        output_sensors: Dict mapping entity_id to sensor state dict.

    """
    for entity_data in output_sensors.values():
        values: list[float] = []

        state_val = _try_parse_float(entity_data["state"])
        if state_val is not None:
            values.append(abs(state_val))

        for item in entity_data["attributes"].get("forecast", []):
            val = _try_parse_float(item.get("value"))
            if val is not None:
                values.append(abs(val))

        decimal_places = _get_decimal_places(max(values)) if values else _DEFAULT_DECIMAL_PLACES

        if state_val is not None:
            rounded_val = round(state_val, decimal_places) + 0.0  # Makes -0.0 into 0.0
            entity_data["state"] = str(rounded_val)

        for item in entity_data["attributes"].get("forecast", []):
            val = _try_parse_float(item.get("value"))
            if val is not None:
                item["value"] = round(val, decimal_places) + 0.0  # Makes -0.0 into 0.0


def get_duration_sensor_entity_id(hass: HomeAssistant, config_entry: ConfigEntry) -> str | None:
    """Get the entity_id of the optimization duration sensor for this config entry.

    Returns None if the sensor hasn't been created yet (no optimization has ever run).
    """
    network_subentry = next(
        (s for s in config_entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK),
        None,
    )
    if network_subentry is None:
        return None
    device_id = build_device_identifier(config_entry, network_subentry, ELEMENT_TYPE_NETWORK)[1]
    unique_id = f"{device_id}_{OUTPUT_NAME_OPTIMIZATION_DURATION}"
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)


def get_horizon_sensor_entity_id(hass: HomeAssistant, config_entry: ConfigEntry) -> str | None:
    """Get the entity_id of the forecast horizon sensor for this config entry.

    Returns None if the sensor hasn't been created yet.
    """
    unique_id = f"{config_entry.entry_id}_{OUTPUT_NAME_HORIZON}"
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)


def get_output_sensors(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, SensorStateDict]:
    """Get all output sensors created by this config entry.

    Returns a dict mapping entity_id to a cleaned sensor state dict.
    Uses State.as_dict() to get complete state information including:
    - entity_id, state, attributes, last_changed, last_updated, context

    Unstable fields that are removed:
    - last_changed, last_updated, context (timestamp-based, not relevant for snapshot comparison)

    Numeric values are rounded intelligently based on their unit's maximum absolute value
    to provide approximately 4 significant figures, reducing noise from floating-point precision.
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
            # Drop internal-only attributes to keep snapshots stable.
            state_dict["attributes"].pop("field_path", None)

        # Remove timestamp-based fields that aren't relevant for functional comparison
        state_dict.pop("last_changed", None)
        state_dict.pop("last_updated", None)
        state_dict.pop("last_reported", None)
        state_dict.pop("context", None)

        # Cast to SensorStateDict after cleaning (state.as_dict() has extra fields we removed)
        output_sensors[entity_entry.entity_id] = cast("SensorStateDict", state_dict)

    # Apply smart rounding to all numeric values
    _apply_smart_rounding(output_sensors)

    return output_sensors
