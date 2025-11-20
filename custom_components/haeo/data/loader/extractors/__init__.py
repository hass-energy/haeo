"""Data extractor package for different energy data providers."""

from collections.abc import Sequence
from enum import StrEnum
from typing import NamedTuple

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from . import aemo_nem, amberelectric, open_meteo_solar_forecast, solcast_solar
from .utils import EntityMetadata, base_unit_for_device_class, convert_to_base_unit, extract_entity_metadata

# Union of all domain literal types from the extractor modules
ExtractorFormat = aemo_nem.Format | amberelectric.Format | open_meteo_solar_forecast.Format | solcast_solar.Format

# Union of all Extractor class types
DataExtractor = (
    type[aemo_nem.Parser]
    | type[amberelectric.Parser]
    | type[open_meteo_solar_forecast.Parser]
    | type[solcast_solar.Parser]
)


# Dictionary mapping domain strings to their extractor classes
FORMATS: dict[ExtractorFormat, DataExtractor] = {
    aemo_nem.DOMAIN: aemo_nem.Parser,
    amberelectric.DOMAIN: amberelectric.Parser,
    open_meteo_solar_forecast.DOMAIN: open_meteo_solar_forecast.Parser,
    solcast_solar.DOMAIN: solcast_solar.Parser,
}


class ExtractedData(NamedTuple):
    """Container for extracted data and metadata."""

    data: Sequence[tuple[int, float]] | float
    """Extracted forecast data, either a sequence of (timestamp, value) tuples or a single float value."""
    unit: str | None
    """Unit of measurement after conversion to base units. (None if unknown)"""


def extract(state: State) -> ExtractedData:
    """Extract data from a State object and convert to base units."""

    # Extract raw data and unit
    data: Sequence[tuple[int, float]] | float
    unit: str | StrEnum | None
    device_class: SensorDeviceClass | None

    if aemo_nem.Parser.detect(state):
        data, unit, device_class = aemo_nem.Parser.extract(state)
    elif amberelectric.Parser.detect(state):
        data, unit, device_class = amberelectric.Parser.extract(state)
    elif open_meteo_solar_forecast.Parser.detect(state):
        data, unit, device_class = open_meteo_solar_forecast.Parser.extract(state)
    elif solcast_solar.Parser.detect(state):
        data, unit, device_class = solcast_solar.Parser.extract(state)
    else:
        # If no extractor matched read the state as a single float value
        data = float(state.state)
        unit = state.attributes.get("unit_of_measurement")
        device_class_attr = state.attributes.get("device_class")
        device_class = SensorDeviceClass(device_class_attr) if device_class_attr else None

    # Normalize unit to string (handle enum values with .value attribute)
    unit_str: str | None = unit.value if isinstance(unit, StrEnum) else unit

    # Get base unit for the device class (if one exists)
    base_unit = base_unit_for_device_class(device_class) or unit_str

    # Convert values to base units
    if isinstance(data, Sequence):
        # Convert each value in the forecast series
        converted_data = [(ts, convert_to_base_unit(value, unit_str, device_class)) for ts, value in data]
        return ExtractedData(converted_data, base_unit)

    # Convert single value
    converted_value = convert_to_base_unit(data, unit_str, device_class)
    return ExtractedData(converted_value, base_unit)


__all__ = [
    "FORMATS",
    "DataExtractor",
    "EntityMetadata",
    "ExtractorFormat",
    "extract",
    "extract_entity_metadata",
]
