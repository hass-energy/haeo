"""Data extractor package for different energy data providers."""

from collections.abc import Sequence
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

# Binary sensor states mapped to numeric values so availability-style
# sources (e.g. an EV charger's "connected" binary sensor) load as 1/0.
_BINARY_STATES: Final[dict[str, float]] = {"on": 1.0, "true": 1.0, "off": 0.0, "false": 0.0}


def parse_scalar_state(raw: str) -> float:
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


def extract(state: EntityState, *, output_type: OutputType | None = None) -> ExtractedData:
    """Extract data from a State object and convert to base units.

    A calendar reads the value typed in each event against the input's output
    type when it is given, so values the input cannot use are ignored.
    """

    # Extract raw data and unit
    data: Sequence[tuple[float, float]] | float
    unit: UnitOfMeasurement | str | None
    device_class: DeviceClass | None

    if calendar_events.Parser.detect(state):
        data, unit, device_class = calendar_events.Parser.extract(state, output_type)
    elif aemo_nem.Parser.detect(state):
        data, unit, device_class = aemo_nem.Parser.extract(state)
    elif amber2mqtt.Parser.detect(state):
        data, unit, device_class = amber2mqtt.Parser.extract(state)
    elif amberelectric.Parser.detect(state):
        data, unit, device_class = amberelectric.Parser.extract(state)
    elif emhass.Parser.detect(state):
        data, unit, device_class = emhass.Parser.extract(state)
    elif flow_power.Parser.detect(state):
        data, unit, device_class = flow_power.Parser.extract(state)
    elif haeo.Parser.detect(state):
        data, unit, device_class = haeo.Parser.extract(state)
    elif nordpool.Parser.detect(state):
        data, unit, device_class = nordpool.Parser.extract(state)
    elif open_meteo_solar_forecast.Parser.detect(state):
        data, unit, device_class = open_meteo_solar_forecast.Parser.extract(state)
    elif solcast_solar.Parser.detect(state):
        data, unit, device_class = solcast_solar.Parser.extract(state)
    elif volcast.Parser.detect(state):
        data, unit, device_class = volcast.Parser.extract(state)
    else:
        # If no extractor matched read the state as a single float value
        data = parse_scalar_state(state.state)
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
    "EntityMetadata",
    "extract",
    "parse_scalar_state",
]
