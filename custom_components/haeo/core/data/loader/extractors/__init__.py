"""Data extractor package for different energy data providers."""

from collections.abc import Callable, Sequence
from datetime import tzinfo
from enum import StrEnum
import math
from typing import Final, NamedTuple, TypeGuard

import numpy as np

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import ON_OFF_STATE_VALUES, EntityState
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

type RawExtracted = tuple[Sequence[tuple[float, float]] | float, UnitOfMeasurement | str | None, DeviceClass | None]
"""A parser's data, with its unit and device class before conversion to base units."""

type Parse = Callable[[EntityState, tzinfo, OutputType | None], RawExtracted | None]
"""Read a state in one format, returning None when the state is not in that format."""


def _forecast_format[S](
    detect: Callable[[EntityState], TypeGuard[S]], extract: Callable[[S, tzinfo], RawExtracted]
) -> Parse:
    """Return a parse function for a forecast format, which reads the same whatever the input."""

    def parse(state: EntityState, time_zone: tzinfo, _output_type: OutputType | None) -> RawExtracted | None:
        return extract(state, time_zone) if detect(state) else None

    return parse


def _calendar(state: EntityState, time_zone: tzinfo, output_type: OutputType | None) -> RawExtracted | None:
    """Read a calendar's events, whose typed values read against the input's output type."""
    return (
        calendar_events.Parser.extract(state, time_zone, output_type) if calendar_events.Parser.detect(state) else None
    )


# Every format a state can be read in, tried in order. Volcast entries also
# carry a Solcast-style pv_estimate, so Volcast comes before Solcast.
PARSERS: Final[tuple[Parse, ...]] = (
    _calendar,
    _forecast_format(aemo_nem.Parser.detect, aemo_nem.Parser.extract),
    _forecast_format(amber2mqtt.Parser.detect, amber2mqtt.Parser.extract),
    _forecast_format(amberelectric.Parser.detect, amberelectric.Parser.extract),
    _forecast_format(emhass.Parser.detect, emhass.Parser.extract),
    _forecast_format(flow_power.Parser.detect, flow_power.Parser.extract),
    _forecast_format(haeo.Parser.detect, haeo.Parser.extract),
    _forecast_format(nordpool.Parser.detect, nordpool.Parser.extract),
    _forecast_format(open_meteo_solar_forecast.Parser.detect, open_meteo_solar_forecast.Parser.extract),
    _forecast_format(volcast.Parser.detect, volcast.Parser.extract),
    _forecast_format(solcast_solar.Parser.detect, solcast_solar.Parser.extract),
)


class ExtractedData[T: Sequence[tuple[float, float]] | float = Sequence[tuple[float, float]] | float](NamedTuple):
    """Container for extracted data and metadata."""

    data: T
    """Extracted forecast data, either a sequence of (timestamp, value) tuples or a single float value."""
    unit: UnitOfMeasurement | str | None
    """Unit of measurement after conversion to base units. (None if unknown)"""


def extract_reading(state: EntityState) -> ExtractedData[float]:
    """Read a state's value now, converted to base units, whatever forecast it carries.

    Binary states read as 1 for on and 0 for off, so availability-style
    sources, such as an EV charger's "connected" binary sensor, load as 1/0.

    Raises:
        ValueError: If the state is not a reading, such as ``unknown`` or a
            value that is not finite, or is a calendar's, whose state only
            says whether an event is on.

    """
    if calendar_events.Parser.detect(state):
        msg = f"Calendar {state.entity_id} has no reading"
        raise ValueError(msg)
    raw = state.state.strip().lower()
    value = ON_OFF_STATE_VALUES[raw] if raw in ON_OFF_STATE_VALUES else float(raw)
    if not math.isfinite(value):
        msg = f"{state.entity_id} reads {state.state}, which is not a finite number"
        raise ValueError(msg)
    unit = state.attributes.get("unit_of_measurement")
    converted, base_unit, _ = convert_to_base_unit(
        value, unit if isinstance(unit, str) else None, DeviceClass.of(state.attributes.get("device_class"))
    )
    return ExtractedData(converted, base_unit)


def extract(state: EntityState, *, time_zone: tzinfo, output_type: OutputType | None = None) -> ExtractedData:
    """Extract data from a State object and convert to base units.

    The state is read in the first of :data:`PARSERS` that recognizes it,
    or as its reading when none does. Timestamps without a time zone are
    read in ``time_zone``, Home Assistant's local time zone.

    A calendar reads the value typed in each event against the input's output
    type when it is given, so values the input cannot use are ignored.

    Raises:
        ValueError: If the state has no data, such as a calendar without
            injected events or a state that is not a reading.

    """
    parsed = next((found for parse in PARSERS if (found := parse(state, time_zone, output_type)) is not None), None)
    if parsed is None:
        reading = extract_reading(state)
        return ExtractedData(reading.data, reading.unit)
    data, unit, device_class = parsed

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
    "PARSERS",
    "EntityMetadata",
    "ExtractedData",
    "Parse",
    "extract",
    "extract_reading",
]
