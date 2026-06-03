"""Utility functions for extracting and processing sensor data."""

from collections.abc import Mapping
import math
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, ELEMENT_TYPE_NETWORK, OUTPUT_NAME_HORIZON, OUTPUT_NAME_OPTIMIZATION_DURATION
from .entities.device import build_device_identifier

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


def _sensor_attributes(attributes: Mapping[str, Any]) -> SensorAttributes:
    """Copy HA state attributes into the sensor snapshot shape."""
    snapshot: SensorAttributes = {}
    unit = attributes.get("unit_of_measurement")
    if isinstance(unit, str):
        snapshot["unit_of_measurement"] = unit
    forecast = attributes.get("forecast")
    if isinstance(forecast, list):
        snapshot["forecast"] = forecast
    return snapshot


def _round_sig(value: float) -> float:
    """Round a value to _TARGET_SIG_FIGS significant figures.

    At 3 sig figs the rounding step is ~0.1% of the value, which is many
    orders of magnitude larger than cross-platform LP solver noise (~1e-13
    relative).  This makes the rounding deterministic without needing any
    midpoint-tie nudging.

    For values >= 1000, ``decimal_places`` goes negative, which makes
    ``round()`` round to tens, hundreds, etc. — true sig-fig behavior.

    Returns 0.0 for zero input.
    """
    if value == 0:
        return 0.0
    decimal_places = _TARGET_SIG_FIGS - math.floor(math.log10(abs(value))) - 1
    return round(value, decimal_places) + 0.0  # +0.0 normalizes -0.0


def _entity_decimal_places(max_abs: float) -> int:
    """Decimal places for an entity based on its largest absolute value.

    Returns 0 when max_abs is zero (no numeric values to constrain).
    """
    if max_abs == 0:
        return 0
    magnitude = math.floor(math.log10(max_abs))
    return max(0, _TARGET_SIG_FIGS - (magnitude + 1))


def _try_parse_float(value: Any) -> float | None:
    """Try to parse a value as float, returning None if not possible."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _apply_smart_rounding(output_sensors: dict[str, SensorStateDict]) -> None:
    """Apply two-pass rounding to numeric values in output sensors.

    Pass 1 — per-value significant figures:
        Each value is independently rounded to _TARGET_SIG_FIGS sig figs.
        This stabilizes every value (including the entity maximum) so that
        floating-point representation noise at rounding midpoints produces
        the same result on all platforms.

    Pass 2 — per-entity decimal-place cap:
        The entity's (now stable) maximum absolute value determines the
        decimal places for _TARGET_SIG_FIGS sig figs at that magnitude.
        All values in the entity are re-rounded to that precision.  This
        suppresses noise-floor values that survived pass 1 with meaningless
        low-order digits.

    The combination is cliff-free: pass 1 ensures the maximum used by pass 2
    is deterministic, and pass 2 ensures small values within a series don't
    retain more precision than the series scale warrants.

    Modifies output_sensors in place.
    """
    for entity_data in output_sensors.values():
        # Pass 1: per-value sig figs
        state_val = _try_parse_float(entity_data["state"])
        state_rounded: float | None = None
        if state_val is not None:
            state_rounded = _round_sig(state_val)

        forecast_rounded: list[tuple[ForecastItem, float]] = []
        for item in entity_data["attributes"].get("forecast", []):
            val = _try_parse_float(item.get("value"))
            if val is not None:
                forecast_rounded.append((item, _round_sig(val)))

        # Pass 2: cap decimal places using the stable max
        abs_values = [abs(v) for _, v in forecast_rounded]
        if state_rounded is not None:
            abs_values.append(abs(state_rounded))

        if not abs_values:
            continue

        dp = _entity_decimal_places(max(abs_values))

        if state_rounded is not None:
            entity_data["state"] = str(round(state_rounded, dp) + 0.0)

        for item, rounded_val in forecast_rounded:
            item["value"] = round(rounded_val, dp) + 0.0


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

        attributes = dict(state.attributes)
        attributes.pop("field_path", None)

        output_sensors[entity_entry.entity_id] = {
            "entity_id": state.entity_id,
            "state": state.state,
            "attributes": _sensor_attributes(attributes),
        }

    # Apply smart rounding to all numeric values
    _apply_smart_rounding(output_sensors)

    return output_sensors
