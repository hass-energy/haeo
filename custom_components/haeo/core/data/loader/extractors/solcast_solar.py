"""Solcast solar forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime, tzinfo
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp, period_means

_LOGGER = logging.getLogger(__name__)

Format = Literal["solcast_solar"]
DOMAIN: Format = "solcast_solar"

# Length of a detailedForecast period, which the integration fixes at the Solcast API default
PERIOD_SECONDS = 30 * 60


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
    UNIT: UnitOfMeasurement = UnitOfMeasurement.KILO_WATT  # Solcast returns kW
    DEVICE_CLASS: DeviceClass = DeviceClass.POWER

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[SolcastSolarState]:
        """Check if data matches Solcast solar forecast format and narrow type."""

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
            and "pv_estimate" in item
            and isinstance(item["pv_estimate"], (int, float))
            and is_parsable_to_datetime(item["period_start"])
            for item in detailed_forecast
        )

    @staticmethod
    def extract(
        state: SolcastSolarState, time_zone: tzinfo
    ) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Solcast solar forecast format.

        Each pv_estimate is the mean power over the 30 minutes from its
        period_start. Solar power varies smoothly, so the means become
        interpolated points at the middle of each period.
        """
        parsed = period_means(
            (
                start := parse_datetime_to_timestamp(item["period_start"], time_zone),
                start + PERIOD_SECONDS,
                item["pv_estimate"],
            )
            for item in state.attributes["detailedForecast"]
        )
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
