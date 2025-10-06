"""Forecast parser package for different energy data providers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

from . import aemo_nem, amberelectric, open_meteo_solar_forecast, solcast_solar

_LOGGER = logging.getLogger(__name__)

# Use open_meteo_solar_forecast parser for watts format as well
ForecastFormat = Literal[aemo_nem.DOMAIN, amberelectric.DOMAIN, open_meteo_solar_forecast.DOMAIN, solcast_solar.DOMAIN]

_FORMATS = {
    aemo_nem.DOMAIN: aemo_nem,
    amberelectric.DOMAIN: amberelectric,
    open_meteo_solar_forecast.DOMAIN: open_meteo_solar_forecast,
    solcast_solar.DOMAIN: solcast_solar,
}


def detect_format(state: SensorEntity) -> ForecastFormat | None:
    """Detect the forecast data format based on its structure.

    Args:
        state: The sensor state

    Returns:
        The detected forecast format

    """

    valid_formats = [domain for domain, parser in _FORMATS.items() if parser.detect(state)]

    if len(valid_formats) == 1:
        return valid_formats[0]

    if len(valid_formats) > 1:
        _LOGGER.warning("Multiple forecast formats detected: %s", valid_formats)

    return None


def parse_forecast_data(state: SensorEntity) -> Sequence[tuple[int, float]] | None:
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

    extractor = _FORMATS.get(parser_type)
    if extractor is None:
        msg = "Unknown forecast format"
        raise ValueError(msg)

    return extractor.extract(state)
