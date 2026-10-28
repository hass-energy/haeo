"""Utility functions for extracting and processing sensor data."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
import math
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from _typeshed import ConvertibleToFloat

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, ELEMENT_TYPE_NETWORK, OUTPUT_NAME_HORIZON, OUTPUT_NAME_OPTIMIZATION_DURATION
from .unique_id import element_output_unique_id, hub_unique_id
from .util import network_subentry

# Target significant figures for rounding.
# Using 3 sig figs ensures cross-platform LP solver degeneracy (different optimal
# vertices with the same cost) rounds to the same value on all architectures.
_TARGET_SIG_FIGS = 3

# Significant figures a value is first snapped to: far finer than the target,
# but coarse enough to absorb the floating-point noise in a solver's result.
_NOISE_SIG_FIGS = 9


class ForecastItem(TypedDict):
    """Single forecast point in sensor attributes."""

    time: datetime | str  # datetime in live state; ISO string once JSON-serialized
    value: float | str  # Numeric or status string (e.g., "success")


# Live Home Assistant state attributes pass through to snapshots as-is (minus
# internal-only keys), so arbitrary keys appear alongside well-known entries
# such as "unit_of_measurement" and "forecast". Downstream consumers (the
# forecast card, scenario snapshots) rely on that full set, which a closed
# TypedDict cannot describe.
SensorAttributes = dict[str, object]


class SensorStateDict(TypedDict):
    """Cleaned sensor state dict returned by get_output_sensors."""

    entity_id: str
    state: str
    attributes: SensorAttributes


def _round_decimal(value: float, decimal_places: int) -> float:
    """Round a value half away from zero to decimal_places, the same on every platform.

    Solver results differ across platforms by noise around 1e-13 relative.
    That decides how a value lying exactly on a rounding midpoint, such as an
    18.25 kWh trip delivered in full, rounds when the binary float is rounded
    directly. Reading the value at _NOISE_SIG_FIGS first removes the noise,
    and rounding that decimal half away from zero settles the midpoint.

    A negative ``decimal_places`` rounds to tens, hundreds, etc.
    """
    snapped = Decimal(f"{value:.{_NOISE_SIG_FIGS}g}")
    rounded = snapped.quantize(Decimal(1).scaleb(-decimal_places), rounding=ROUND_HALF_UP)
    return float(rounded) + 0.0  # +0.0 normalizes -0.0


def _round_sig(value: float) -> float:
    """Round a value to _TARGET_SIG_FIGS significant figures.

    Returns 0.0 for zero input.
    """
    if value == 0:
        return 0.0
    return _round_decimal(value, _TARGET_SIG_FIGS - math.floor(math.log10(abs(value))) - 1)


def _entity_decimal_places(max_abs: float) -> int:
    """Decimal places for an entity based on its largest absolute value.

    Returns 0 when max_abs is zero (no numeric values to constrain).
    """
    if max_abs == 0:
        return 0
    magnitude = math.floor(math.log10(max_abs))
    return max(0, _TARGET_SIG_FIGS - (magnitude + 1))


def _try_parse_float(value: "ConvertibleToFloat") -> float | None:
    """Try to parse a value as float, returning None if not possible."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _apply_smart_rounding(output_sensors: dict[str, SensorStateDict]) -> None:
    """Round numeric values in output sensors to a precision set by each entity's scale.

    The entity's largest absolute value, rounded to _TARGET_SIG_FIGS sig figs
    so that it is the same on all platforms, determines the decimal places
    for _TARGET_SIG_FIGS sig figs at that magnitude. Every value in the entity
    is rounded once to that precision. This suppresses noise-floor values
    with meaningless low-order digits, and keeps small values within a series
    from retaining more precision than the series scale warrants.

    Modifies output_sensors in place.
    """
    for entity_data in output_sensors.values():
        state_val = _try_parse_float(entity_data["state"])

        forecast_values: list[tuple[ForecastItem, float]] = []
        forecast_attr = entity_data["attributes"].get("forecast")
        forecast_items: list[ForecastItem] = forecast_attr if isinstance(forecast_attr, list) else []
        for item in forecast_items:
            val = _try_parse_float(item.get("value"))
            if val is not None:
                forecast_values.append((item, val))

        abs_values = [abs(_round_sig(v)) for _, v in forecast_values]
        if state_val is not None:
            abs_values.append(abs(_round_sig(state_val)))

        if not abs_values:
            continue

        dp = _entity_decimal_places(max(abs_values))

        if state_val is not None:
            entity_data["state"] = str(_round_decimal(state_val, dp))

        for item, val in forecast_values:
            item["value"] = _round_decimal(val, dp)


def get_duration_sensor_entity_id(hass: HomeAssistant, config_entry: ConfigEntry) -> str | None:
    """Get the entity_id of the optimization duration sensor for this config entry.

    Returns None if the sensor hasn't been created yet (no optimization has ever run).
    """
    unique_id = element_output_unique_id(
        config_entry.entry_id,
        network_subentry(config_entry).subentry_id,
        ELEMENT_TYPE_NETWORK,
        OUTPUT_NAME_OPTIMIZATION_DURATION,
    )
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)


def get_horizon_sensor_entity_id(hass: HomeAssistant, config_entry: ConfigEntry) -> str | None:
    """Get the entity_id of the forecast horizon sensor for this config entry.

    Returns None if the sensor hasn't been created yet.
    """
    unique_id = hub_unique_id(config_entry.entry_id, OUTPUT_NAME_HORIZON)
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)


def get_output_sensors(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, SensorStateDict]:
    """Get all output sensors created by this config entry.

    Returns a dict mapping entity_id to a cleaned sensor state dict.
    Each entry includes entity_id, state, and the live state attributes with
    internal-only keys (field_path) removed. Timestamp and context fields from
    live state are not included.

    Numeric values are rounded intelligently based on their unit's maximum absolute value
    to provide approximately 3 significant figures, reducing noise from floating-point precision.
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

        attributes: SensorAttributes = dict(state.attributes)
        # Drop internal-only attributes to keep snapshots stable.
        attributes.pop("field_path", None)

        output_sensors[entity_entry.entity_id] = {
            "entity_id": state.entity_id,
            "state": state.state,
            "attributes": attributes,
        }

    # Apply smart rounding to all numeric values
    _apply_smart_rounding(output_sensors)

    return output_sensors
