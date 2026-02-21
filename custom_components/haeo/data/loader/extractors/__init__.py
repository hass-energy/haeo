"""Data extractor package for different energy data providers."""

from collections.abc import Sequence
from enum import StrEnum
from typing import NamedTuple

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement, convert_to_base_unit

from . import aemo_nem, amber2mqtt, amberelectric, emhass, flow_power, haeo, open_meteo_solar_forecast, solcast_solar
from .utils import EntityMetadata, extract_entity_metadata, separate_duplicate_timestamps

# Union of all domain literal types from the extractor modules
ExtractorFormat = (
    aemo_nem.Format
    | amber2mqtt.Format
    | amberelectric.Format
    | emhass.Format
    | flow_power.Format
    | haeo.Format
    | open_meteo_solar_forecast.Format
    | solcast_solar.Format
)

# Union of all Extractor class types
DataExtractor = (
    type[aemo_nem.Parser]
    | type[amber2mqtt.Parser]
    | type[amberelectric.Parser]
    | type[emhass.Parser]
    | type[flow_power.Parser]
    | type[haeo.Parser]
    | type[open_meteo_solar_forecast.Parser]
    | type[solcast_solar.Parser]
)


# Dictionary mapping domain strings to their extractor classes
FORMATS: dict[ExtractorFormat, DataExtractor] = {
    aemo_nem.DOMAIN: aemo_nem.Parser,
    amber2mqtt.DOMAIN: amber2mqtt.Parser,
    amberelectric.DOMAIN: amberelectric.Parser,
    emhass.DOMAIN: emhass.Parser,
    flow_power.DOMAIN: flow_power.Parser,
    haeo.DOMAIN: haeo.Parser,
    open_meteo_solar_forecast.DOMAIN: open_meteo_solar_forecast.Parser,
    solcast_solar.DOMAIN: solcast_solar.Parser,
}


class ExtractedData(NamedTuple):
    """Container for extracted data and metadata."""

    data: Sequence[tuple[float, float]] | float
    """Extracted forecast data, either a sequence of (timestamp, value) tuples or a single float value."""
    unit: UnitOfMeasurement | str | None
    """Unit of measurement after conversion to base units. (None if unknown)"""


def extract(state: EntityState) -> ExtractedData:
    """Extract data from a State object and convert to base units."""

    # Extract raw data and unit
    data: Sequence[tuple[int, float]] | float
    unit: UnitOfMeasurement | str | None
    device_class: DeviceClass | None

    if aemo_nem.Parser.detect(state):
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
    elif open_meteo_solar_forecast.Parser.detect(state):
        data, unit, device_class = open_meteo_solar_forecast.Parser.extract(state)
    elif solcast_solar.Parser.detect(state):
        data, unit, device_class = solcast_solar.Parser.extract(state)
    else:
        # If no extractor matched read the state as a single float value
        data = float(state.state)
        unit = state.attributes.get("unit_of_measurement")
        device_class_attr = state.attributes.get("device_class")
        device_class = DeviceClass.of(device_class_attr)

    # Normalize unit to string (handle enum values with .value attribute)
    unit_str: str | None = unit.value if isinstance(unit, StrEnum) else unit

    # Convert values to base units
    if isinstance(data, Sequence):
        converted_data: list[tuple[int, float]] = []
        base_unit: UnitOfMeasurement | str | None = unit_str
        for ts, point_value in data:
            converted_value, base_unit, _ = convert_to_base_unit(
                point_value,
                unit_str,
                device_class,
            )
            converted_data.append((ts, converted_value))

        # Separate duplicate timestamps to prevent interpolation (also converts int timestamps to float)
        separated_data = separate_duplicate_timestamps(converted_data)
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
    "extract_entity_metadata",
]
