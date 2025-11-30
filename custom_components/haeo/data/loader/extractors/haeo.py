"""HAEO forecast parser.

Parses forecast data from HAEO's own output format, which uses a "forecast"
attribute containing a mapping of datetime keys to float values.
"""

from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import datetime
import logging
from typing import Literal, NotRequired, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["haeo"]
DOMAIN: Format = "haeo"


class HaeoForecastPoint(TypedDict):
    """Single point in a HAEO forecast time series."""

    time: str | datetime
    value: int | float


class HaeoForecastAttributes(TypedDict):
    """Type definition for HAEO forecast State attributes."""

    forecast: Sequence[HaeoForecastPoint]
    unit_of_measurement: str
    device_class: NotRequired[str]


class HaeoForecastState(Protocol):
    """Protocol for a State object with validated HAEO forecast data."""

    attributes: HaeoForecastAttributes


class Parser:
    """Parser for HAEO forecast data.

    Unlike other parsers, this one derives unit and device_class from the
    entity state attributes rather than using hardcoded values.
    """

    DOMAIN: Format = DOMAIN

    @staticmethod
    def detect(state: State) -> TypeGuard[HaeoForecastState]:
        """Check if data matches HAEO forecast format and narrow type."""
        # Check for required forecast attribute
        if "forecast" not in state.attributes:
            return False

        forecast = state.attributes["forecast"]

        # Only support list format: list of {"time": ..., "value": ...} dicts
        if not isinstance(forecast, Sequence) or isinstance(forecast, str):
            return False

        if not forecast:
            return False

        # Validate all entries are dicts with time and value fields
        if not all(
            isinstance(item, Mapping)
            and "time" in item
            and "value" in item
            and is_parsable_to_datetime(item["time"])
            and isinstance(item["value"], (int, float))
            for item in forecast
        ):
            return False

        # Check for required unit_of_measurement
        unit = state.attributes.get("unit_of_measurement")
        if not isinstance(unit, str) or not unit:
            return False

        # device_class is optional, but if present must be a string
        device_class = state.attributes.get("device_class")
        return device_class is None or isinstance(device_class, str)

    @staticmethod
    def extract(state: HaeoForecastState) -> tuple[Sequence[tuple[int, float]], str, SensorDeviceClass | None]:
        """Extract forecast data from HAEO forecast format.

        Expects list format: list of {"time": ..., "value": ...} dicts.

        Returns:
            Tuple of (forecast_data, unit, device_class) where unit and device_class
            are derived from the entity state attributes.

        """
        forecast = state.attributes["forecast"]

        # Parse list of {"time": ..., "value": ...} dicts
        parsed = [
            (parse_datetime_to_timestamp(item["time"]), float(item["value"]))
            for item in forecast
        ]
        parsed.sort(key=lambda x: x[0])

        unit = state.attributes["unit_of_measurement"]

        device_class_attr = state.attributes.get("device_class")
        device_class: SensorDeviceClass | None = None
        if device_class_attr:
            with suppress(ValueError):
                device_class = SensorDeviceClass(device_class_attr)

        return parsed, unit, device_class
