"""Data extractor package for different energy data providers."""

from collections.abc import Sequence
from datetime import tzinfo
from enum import StrEnum
from typing import Final, NamedTuple

import numpy as np

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement, base_unit_conversion, convert_to_base_unit

from . import (
    aemo_nem,
    amber2mqtt,
    amberelectric,
    calendar_events,
    emhass,
    flow_power,
    haeo,
    nordpool,
    open_meteo_solar_forecast,
    solcast_solar,
    volcast,
)
from .utils import EntityMetadata, separate_duplicate_timestamps

# Union of all domain literal types from the extractor modules
ExtractorFormat = (
    aemo_nem.Format
    | amber2mqtt.Format
    | amberelectric.Format
    | calendar_events.Format
    | emhass.Format
    | flow_power.Format
    | haeo.Format
    | nordpool.Format
    | open_meteo_solar_forecast.Format
    | solcast_solar.Format
    | volcast.Format
)

# Union of all Extractor class types
DataExtractor = (
    type[aemo_nem.Parser]
    | type[amber2mqtt.Parser]
    | type[amberelectric.Parser]
    | type[calendar_events.Parser]
    | type[emhass.Parser]
    | type[flow_power.Parser]
    | type[haeo.Parser]
    | type[nordpool.Parser]
    | type[open_meteo_solar_forecast.Parser]
    | type[solcast_solar.Parser]
    | type[volcast.Parser]
)


# Dictionary mapping domain strings to their extractor classes
FORMATS: dict[ExtractorFormat, DataExtractor] = {
    aemo_nem.DOMAIN: aemo_nem.Parser,
    amber2mqtt.DOMAIN: amber2mqtt.Parser,
    amberelectric.DOMAIN: amberelectric.Parser,
    calendar_events.DOMAIN: calendar_events.Parser,
    emhass.DOMAIN: emhass.Parser,
    flow_power.DOMAIN: flow_power.Parser,
    haeo.DOMAIN: haeo.Parser,
    nordpool.DOMAIN: nordpool.Parser,
    open_meteo_solar_forecast.DOMAIN: open_meteo_solar_forecast.Parser,
    solcast_solar.DOMAIN: solcast_solar.Parser,
    volcast.DOMAIN: volcast.Parser,
}


# Binary sensor states mapped to numeric values so availability-style
# sources (e.g. an EV charger's "connected" binary sensor) load as 1/0.
_BINARY_STATES: Final[dict[str, float]] = {"on": 1.0, "true": 1.0, "off": 0.0, "false": 0.0}


def _parse_scalar_state(raw: str) -> float:
    """Parse a state string as a float, mapping binary on/off states to 1/0."""
    mapped = _BINARY_STATES.get(raw.strip().lower())
    if mapped is not None:
        return mapped
    return float(raw)


class ExtractedData(NamedTuple):
    """Container for extracted data and metadata."""

    data: Sequence[tuple[float, float]] | float
    """Extracted forecast data, either a sequence of (timestamp, value) tuples or a single float value."""
    unit: UnitOfMeasurement | str | None
    """Unit of measurement after conversion to base units. (None if unknown)"""


def extract(state: EntityState, *, time_zone: tzinfo, output_type: OutputType | None = None) -> ExtractedData:
    """Extract data from a State object and convert to base units.

    Timestamps without a time zone are read in ``time_zone``, Home Assistant's
    local time zone.

    A calendar reads the value typed in each event against the input's output
    type when it is given, so values the input cannot use are ignored.
    """

    # Extract raw data and unit
    data: Sequence[tuple[float, float]] | float
    unit: UnitOfMeasurement | str | None
    device_class: DeviceClass | None

    if calendar_events.Parser.detect(state):
        data, unit, device_class = calendar_events.Parser.extract(state, time_zone, output_type)
    elif aemo_nem.Parser.detect(state):
        data, unit, device_class = aemo_nem.Parser.extract(state, time_zone)
    elif amber2mqtt.Parser.detect(state):
        data, unit, device_class = amber2mqtt.Parser.extract(state, time_zone)
    elif amberelectric.Parser.detect(state):
        data, unit, device_class = amberelectric.Parser.extract(state, time_zone)
    elif emhass.Parser.detect(state):
        data, unit, device_class = emhass.Parser.extract(state, time_zone)
    elif flow_power.Parser.detect(state):
        data, unit, device_class = flow_power.Parser.extract(state, time_zone)
    elif haeo.Parser.detect(state):
        data, unit, device_class = haeo.Parser.extract(state, time_zone)
    elif nordpool.Parser.detect(state):
        data, unit, device_class = nordpool.Parser.extract(state, time_zone)
    elif open_meteo_solar_forecast.Parser.detect(state):
        data, unit, device_class = open_meteo_solar_forecast.Parser.extract(state, time_zone)
    elif solcast_solar.Parser.detect(state):
        data, unit, device_class = solcast_solar.Parser.extract(state, time_zone)
    elif volcast.Parser.detect(state):
        data, unit, device_class = volcast.Parser.extract(state, time_zone)
    else:
        # If no extractor matched read the state as a single float value
        data = _parse_scalar_state(state.state)
        unit_attr = state.attributes.get("unit_of_measurement")
        unit = unit_attr if isinstance(unit_attr, str) else None
        device_class = DeviceClass.of(state.attributes.get("device_class"))

    # Normalize unit to string (handle enum values with .value attribute)
    unit_str: str | None = unit.value if isinstance(unit, StrEnum) else unit

    # Convert values to base units
    if isinstance(data, Sequence):
        factor, base_unit, _ = base_unit_conversion(unit_str, device_class)
        points = np.asarray(data, dtype=np.float64).reshape(-1, 2)

        # Separate duplicate timestamps to prevent interpolation
        separated_data = separate_duplicate_timestamps(points[:, 0], points[:, 1] * factor)
        return ExtractedData(separated_data, base_unit)

    # Convert single value
    converted_value, base_unit, _ = convert_to_base_unit(data, unit_str, device_class)
    return ExtractedData(converted_value, base_unit)


__all__ = [
    "FORMATS",
    "DataExtractor",
    "EntityMetadata",
    "ExtractorFormat",
    "extract",
]
