"""Solcast solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import State

from custom_components.haeo.helpers.types import is_sequence

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["solcast_solar"]
DOMAIN: Format = "solcast_solar"


class SolcastForecastEntry(TypedDict):
    """Type definition for a Solcast forecast entry."""

    period_start: str | datetime
    pv_estimate: float


class SolcastSolarAttributes(TypedDict):
    """Type definition for Solcast solar forecast State attributes."""

    detailedForecast: Sequence[SolcastForecastEntry]


class SolcastSolarState(Protocol):
    """Protocol for a State object with validated Solcast solar forecast data."""

    attributes: SolcastSolarAttributes


class Parser:
    """Parser for Solcast solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = UnitOfPower.KILO_WATT  # Solcast returns kW
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.POWER

    @staticmethod
    def detect(state: State) -> TypeGuard[SolcastSolarState]:
        """Check if data matches Solcast solar forecast format and narrow type."""

        if "detailedForecast" not in state.attributes:
            return False

        detailed_forecast = state.attributes["detailedForecast"]
        if (
            not (is_sequence(detailed_forecast) and not isinstance(detailed_forecast, (str, bytes)))
            or not detailed_forecast
        ):
            return False

        return all(
            isinstance(item, Mapping)
            and "period_start" in item
            and "pv_estimate" in item
            and isinstance(item["pv_estimate"], (int, float))
            and is_parsable_to_datetime(item["period_start"])
            for item in detailed_forecast
        )

    @staticmethod
    def extract(state: SolcastSolarState) -> tuple[Sequence[tuple[int, float]], str, SensorDeviceClass]:
        """Extract forecast data from Solcast solar forecast format.

        State has been validated by detect(), so all entries are guaranteed to be valid.
        """
        parsed: list[tuple[int, float]] = [
            (parse_datetime_to_timestamp(item["period_start"]), item["pv_estimate"])
            for item in state.attributes["detailedForecast"]
        ]
        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
