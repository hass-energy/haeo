"""AEMO energy market forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["aemo_nem"]
DOMAIN: Format = "aemo_nem"


class AemoForecastEntry(TypedDict):
    """Type definition for an AEMO forecast entry."""

    start_time: str | datetime
    price: float


class AemoNemAttributes(TypedDict):
    """Type definition for AEMO NEM State attributes."""

    forecast: Sequence[AemoForecastEntry]


class AemoNemState(Protocol):
    """Protocol for a State object with validated AEMO NEM forecast data."""

    attributes: AemoNemAttributes


class Parser:
    """Parser for AEMO energy market forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = "$/kWh"  # AEMO prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> TypeGuard[AemoNemState]:
        """Check if data matches AEMO energy market format and narrow type."""

        if "forecast" not in state.attributes:
            return False

        forecast = state.attributes["forecast"]
        if not (isinstance(forecast, Sequence) and not isinstance(forecast, (str, bytes))) or not forecast:
            return False

        return all(
            isinstance(item, Mapping)
            and "start_time" in item
            and "price" in item
            and isinstance(item["price"], (int, float))
            and is_parsable_to_datetime(item["start_time"])
            for item in forecast
        )

    @staticmethod
    def extract(state: AemoNemState) -> tuple[Sequence[tuple[float, float]], str, SensorDeviceClass]:
        """Extract forecast data from AEMO energy market format."""
        parsed: list[tuple[float, float]] = [
            (parse_datetime_to_timestamp(item["start_time"]), item["price"]) for item in state.attributes["forecast"]
        ]
        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
