"""Open-Meteo solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, NotRequired, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp, step_points

_LOGGER = logging.getLogger(__name__)

Format = Literal["open_meteo_solar_forecast"]
DOMAIN: Format = "open_meteo_solar_forecast"

# Length of a wh_period_15m period
PERIOD_SECONDS = 15 * 60
PERIODS_PER_HOUR = 3600 // PERIOD_SECONDS


class OpenMeteoSolarAttributes(TypedDict):
    """Type definition for Open-Meteo solar forecast State attributes."""

    watts: Mapping[str | datetime, float]
    wh_period_15m: NotRequired[Mapping[str | datetime, float]]


class OpenMeteoSolarState(Protocol):
    """Protocol for a State object with validated Open-Meteo solar forecast data."""

    attributes: OpenMeteoSolarAttributes


class Parser:
    """Parser for Open-Meteo solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: UnitOfMeasurement = UnitOfMeasurement.WATT  # Data is in watts
    DEVICE_CLASS: DeviceClass = DeviceClass.POWER

    @staticmethod
    def _is_series(series: object) -> bool:
        """Check that a value maps timestamps to numbers."""
        return (
            isinstance(series, Mapping)
            and bool(series)
            and all(is_parsable_to_datetime(k) and isinstance(v, (int, float)) for k, v in series.items())
        )

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[OpenMeteoSolarState]:
        """Check if data matches Open-Meteo solar forecast format and narrow type."""
        attributes = state.attributes
        return Parser._is_series(attributes.get("watts")) and (
            "wh_period_15m" not in attributes or Parser._is_series(attributes["wh_period_15m"])
        )

    @staticmethod
    def extract(state: OpenMeteoSolarState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Open-Meteo solar forecast format.

        Each wh_period_15m value is the energy over the 15 minutes from its
        timestamp, so its mean power holds across that period as a step
        function. Integration versions before 0.1.31 publish only watts, whose
        values are read as points at their timestamps.
        """
        attributes = state.attributes
        if "wh_period_15m" in attributes:
            parsed = step_points(
                (start := parse_datetime_to_timestamp(time), start + PERIOD_SECONDS, energy * PERIODS_PER_HOUR)
                for time, energy in attributes["wh_period_15m"].items()
            )
        else:
            parsed = sorted((parse_datetime_to_timestamp(time), value) for time, value in attributes["watts"].items())
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
