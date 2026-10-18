"""Open-Meteo solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["open_meteo_solar_forecast"]
DOMAIN: Format = "open_meteo_solar_forecast"

# How far each watts value's timestamp is ahead of the instant its power is for.
# The library computes watts from Open-Meteo's instantaneous irradiance, which
# applies at its own timestamp, but keys it 15 minutes earlier, as it does the
# preceding 15 minute means.
WATTS_OFFSET_SECONDS = 15 * 60


class OpenMeteoSolarAttributes(TypedDict):
    """Type definition for Open-Meteo solar forecast State attributes."""

    watts: Mapping[str | datetime, float]


class OpenMeteoSolarState(Protocol):
    """Protocol for a State object with validated Open-Meteo solar forecast data."""

    attributes: OpenMeteoSolarAttributes


class Parser:
    """Parser for Open-Meteo solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: UnitOfMeasurement = UnitOfMeasurement.WATT  # Data is in watts
    DEVICE_CLASS: DeviceClass = DeviceClass.POWER

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[OpenMeteoSolarState]:
        """Check if data matches Open-Meteo solar forecast format and narrow type."""

        if "watts" not in state.attributes:
            return False

        watts = state.attributes["watts"]
        if not isinstance(watts, Mapping) or not watts:
            return False

        return all(is_parsable_to_datetime(k) and isinstance(v, (int, float)) for k, v in watts.items())

    @staticmethod
    def extract(state: OpenMeteoSolarState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Open-Meteo solar forecast format.

        Each watts value is the instantaneous power 15 minutes after its
        timestamp, so it is placed at that instant and the fuser interpolates
        between instants.
        """
        parsed = sorted(
            (parse_datetime_to_timestamp(time) + WATTS_OFFSET_SECONDS, value)
            for time, value in state.attributes["watts"].items()
        )
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
