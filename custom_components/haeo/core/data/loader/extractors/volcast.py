"""Volcast solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from itertools import pairwise
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp, period_means

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
        Solar power varies smoothly, so the means become interpolated points at
        the middle of each period. Volcast leaves out periods with no output, so
        a zero period is added at each end of every gap and of the forecast,
        making the power zero across the gaps and through the night.
        """
        blocks = sorted(
            (start := parse_datetime_to_timestamp(item["period_start"]), start + PERIOD_SECONDS, item["power_w"])
            for item in state.attributes["detailedForecast"]
        )
        # Zero periods just before the forecast, just after it, and at both ends of each gap
        zero_starts = {blocks[0][0] - PERIOD_SECONDS, blocks[-1][1]}
        for (_, end, _), (start, _, _) in pairwise(blocks):
            if start > end:
                zero_starts |= {end, start - PERIOD_SECONDS}
        parsed = period_means([*blocks, *((start, start + PERIOD_SECONDS, 0.0) for start in zero_starts)])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
