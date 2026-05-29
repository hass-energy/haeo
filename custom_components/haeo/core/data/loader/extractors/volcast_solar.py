"""Volcast solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["volcast_solar"]
DOMAIN: Format = "volcast_solar"


class VolcastForecastEntry(TypedDict):
    """Type definition for a Volcast forecast entry."""

    period_start: str | datetime
    power_w: int | float


class VolcastSolarAttributes(TypedDict):
    """Type definition for Volcast solar forecast state attributes."""

    detailedForecast: Sequence[VolcastForecastEntry]


class VolcastSolarState(Protocol):
    """Protocol for a State object with validated Volcast solar forecast data."""

    attributes: VolcastSolarAttributes


class Parser:
    """Parser for Volcast solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: UnitOfMeasurement = UnitOfMeasurement.WATT  # Volcast detailedForecast returns W
    DEVICE_CLASS: DeviceClass = DeviceClass.POWER

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[VolcastSolarState]:
        """Check if data matches Volcast solar forecast format and narrow type."""

        if "detailedForecast" not in state.attributes:
            return False

        detailed_forecast = state.attributes["detailedForecast"]
        if (
            not (isinstance(detailed_forecast, Sequence) and not isinstance(detailed_forecast, (str, bytes)))
            or not detailed_forecast
        ):
            return False

        return all(
            isinstance(item, Mapping)
            and "period_start" in item
            and "power_w" in item
            and isinstance(item["power_w"], (int, float))
            and is_parsable_to_datetime(item["period_start"])
            for item in detailed_forecast
        )

    @staticmethod
    def extract(state: VolcastSolarState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Volcast solar forecast format.

        State has been validated by detect(), so all entries are guaranteed to be valid.
        """
        parsed: list[tuple[int, float]] = [
            (parse_datetime_to_timestamp(item["period_start"]), item["power_w"])
            for item in state.attributes["detailedForecast"]
        ]
        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
