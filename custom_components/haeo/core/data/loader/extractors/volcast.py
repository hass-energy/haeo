"""Volcast solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from itertools import pairwise
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["volcast"]
DOMAIN: Format = "volcast"

# Length of a detailedForecast period
PERIOD_SECONDS = 5 * 60


class VolcastForecastEntry(TypedDict):
    """Type definition for a Volcast forecast entry."""

    period_start: str | datetime
    power_w: int | float


class VolcastAttributes(TypedDict):
    """Type definition for Volcast state attributes."""

    detailedForecast: Sequence[VolcastForecastEntry]


class VolcastState(Protocol):
    """Protocol for a State object with validated Volcast forecast data."""

    attributes: VolcastAttributes


class Parser:
    """Parser for Volcast solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: UnitOfMeasurement = UnitOfMeasurement.WATT  # Volcast detailedForecast returns W
    DEVICE_CLASS: DeviceClass = DeviceClass.POWER

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[VolcastState]:
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
    def extract(state: VolcastState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Volcast format.

        Each power_w is the mean power over the 5 minutes from its period_start.
        Solar power varies smoothly, so the mean is placed at the middle of its
        period and the fuser interpolates between periods. Volcast leaves out
        periods with no output, so the first and last period of each gap get a
        zero point and the power is zero across the gap.
        """
        points = sorted(
            (parse_datetime_to_timestamp(item["period_start"]) + PERIOD_SECONDS // 2, item["power_w"])
            for item in state.attributes["detailedForecast"]
        )
        gaps = {
            zero_time
            for (time, _), (next_time, _) in pairwise(points)
            if next_time - time > PERIOD_SECONDS
            for zero_time in (time + PERIOD_SECONDS, next_time - PERIOD_SECONDS)
        }
        parsed = sorted([*points, *((time, 0.0) for time in gaps)])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
