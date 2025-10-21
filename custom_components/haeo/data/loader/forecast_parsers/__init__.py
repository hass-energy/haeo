"""Forecast parser package for different energy data providers."""

from collections.abc import Sequence
import logging

from homeassistant.core import State

from . import aemo_nem, amberelectric, open_meteo_solar_forecast, solcast_solar

_LOGGER = logging.getLogger(__name__)

# Union of all domain literal types from the parser modules
ForecastFormat = aemo_nem.Format | amberelectric.Format | open_meteo_solar_forecast.Format | solcast_solar.Format

# Union of all Parser class types
ForecastParser = (
    type[aemo_nem.Parser]
    | type[amberelectric.Parser]
    | type[open_meteo_solar_forecast.Parser]
    | type[solcast_solar.Parser]
)

# Dictionary mapping domain strings to their parser classes
_FORMATS: dict[ForecastFormat, ForecastParser] = {
    aemo_nem.DOMAIN: aemo_nem.Parser,
    amberelectric.DOMAIN: amberelectric.Parser,
    open_meteo_solar_forecast.DOMAIN: open_meteo_solar_forecast.Parser,
    solcast_solar.DOMAIN: solcast_solar.Parser,
}


def detect_format(state: State) -> ForecastFormat | None:
    """Detect the forecast data format based on its structure."""

    valid_formats: list[ForecastFormat] = [domain for domain, parser in _FORMATS.items() if parser.detect(state)]

    if len(valid_formats) == 1:
        return valid_formats[0]

    if len(valid_formats) > 1:
        _LOGGER.warning("Multiple forecast formats detected: %s", valid_formats)

    return None


def parse_forecast_data(state: State) -> Sequence[tuple[int, float]] | None:
    """Parse forecast data into standardized (timestamp_seconds, value) format.

    Args:
        state: The sensor state

    Returns:
        List of (timestamp_seconds, value) tuples sorted by timestamp

    Raises:
        ValueError: If the forecast format is unknown or data is malformed

    """
    parser_type = detect_format(state)

    if parser_type is None:
        return None

    # Since parser_type is a valid ForecastFormat, it must exist in _FORMATS
    return _FORMATS[parser_type].extract(state)


def get_forecast_units(state: State) -> tuple[str | None, str | None]:
    """Get the unit and device class for forecast data.

    Args:
        state: The sensor state

    Returns:
        Tuple of (unit, device_class) for the forecast data, or (None, None) if unknown

    """
    parser_type = detect_format(state)

    if parser_type is None:
        return None, None

    # Since parser_type is a valid ForecastFormat, it must exist in _FORMATS
    parser = _FORMATS[parser_type]
    unit = getattr(parser, "UNIT", None)
    device_class = getattr(parser, "DEVICE_CLASS", None)
    return unit, device_class
