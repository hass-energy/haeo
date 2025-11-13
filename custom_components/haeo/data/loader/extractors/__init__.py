"""Data extractor package for different energy data providers."""

from . import aemo_nem, amberelectric, open_meteo_solar_forecast, solcast_solar
from .utils import EntityMetadata, detect_format, extract_entity_metadata, extract_time_series, get_extracted_units

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

__all__ = [
    "DataExtractor",
    "EntityMetadata",
    "ExtractorFormat",
    "detect_format",
    "extract_entity_metadata",
    "extract_time_series",
    "get_extracted_units",
]
