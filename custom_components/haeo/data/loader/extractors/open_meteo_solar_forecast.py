"""Open-Meteo solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import State

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["open_meteo_solar_forecast"]
DOMAIN: Format = "open_meteo_solar_forecast"


class OpenMeteoSolarAttributes(TypedDict):
    """Type definition for Open-Meteo solar forecast State attributes."""

    watts: Mapping[str | datetime, float]


class OpenMeteoSolarState(Protocol):
    """Protocol for a State object with validated Open-Meteo solar forecast data."""

    attributes: OpenMeteoSolarAttributes


class Parser:
    """Parser for Open-Meteo solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = UnitOfPower.WATT  # Data is in watts
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.POWER

    @staticmethod
    def detect(state: State) -> TypeGuard[OpenMeteoSolarState]:
        """Check if data matches Open-Meteo solar forecast format and narrow type."""

        if "watts" not in state.attributes:
            return False

        watts = state.attributes["watts"]
        if not isinstance(watts, Mapping) or not watts:
            return False

        return all(is_parsable_to_datetime(k) and isinstance(v, (int, float)) for k, v in watts.items())

    @staticmethod
    def extract(state: OpenMeteoSolarState) -> tuple[Sequence[tuple[int, float]], str, SensorDeviceClass]:
        """Extract forecast data from Open-Meteo solar forecast format."""
        parsed: list[tuple[int, float]] = [
            (int(parse_datetime_to_timestamp(time)), value) for time, value in state.attributes["watts"].items()
        ]
        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
