"""Data extractor package for different energy data providers."""

from collections.abc import Sequence
from enum import StrEnum

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from custom_components.haeo.const import convert_to_base_unit

from . import aemo_nem, amberelectric, open_meteo_solar_forecast, solcast_solar
from .utils import EntityMetadata, extract_entity_metadata

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
_FORMATS: dict[ExtractorFormat, DataExtractor] = {
    aemo_nem.DOMAIN: aemo_nem.Parser,
    amberelectric.DOMAIN: amberelectric.Parser,
    open_meteo_solar_forecast.DOMAIN: open_meteo_solar_forecast.Parser,
    solcast_solar.DOMAIN: solcast_solar.Parser,
}


def extract(state: State) -> tuple[Sequence[tuple[int, float]] | float, str | None]:
    """Extract forecast data from a State object and convert to base units.

    Returns a tuple of (data, unit) where:
    - data is either a sequence of (timestamp, value) tuples or a single float value
    - unit is the unit of measurement after conversion to base units
    - values are converted to base units (kW for power, kWh for energy)
    """

    # Extract raw data and unit
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
        device_class = (
            SensorDeviceClass(state.attributes.get("device_class")) if state.attributes.get("device_class") else None
        )

    # Normalize unit to string (handle enum values with .value attribute)
    unit_str: str | None = unit.value if isinstance(unit, StrEnum) else unit

    # Convert values to base units
    if isinstance(data, Sequence):
        # Convert each value in the forecast series
        converted_data = [(ts, convert_to_base_unit(value, unit_str, device_class)) for ts, value in data]
        return converted_data, unit_str

    # Convert single value
    converted_value = convert_to_base_unit(data, unit_str, device_class)
    return converted_value, unit_str


__all__ = [
    "DataExtractor",
    "EntityMetadata",
    "ExtractorFormat",
    "extract",
    "extract_entity_metadata",
]
