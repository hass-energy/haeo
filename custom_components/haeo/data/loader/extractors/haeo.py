"""HAEO forecast parser.

Parses forecast data from HAEO's own output format, which uses a "forecast"
attribute containing a mapping of datetime keys to float values.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, NotRequired, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["haeo"]
DOMAIN: Format = "haeo"


class HaeoForecastAttributes(TypedDict):
    """Type definition for HAEO forecast State attributes."""

    forecast: Mapping[str | datetime, int | float]
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
        if not isinstance(forecast, Mapping) or not forecast:
            return False

        # Validate all forecast entries have valid datetime keys and numeric values
        if not all(
            is_parsable_to_datetime(k) and isinstance(v, (int, float)) for k, v in forecast.items()
        ):
            return False

        # Check for required unit_of_measurement
        unit = state.attributes.get("unit_of_measurement")
        if not isinstance(unit, str):
            return False

        # device_class is optional, but if present must be a string
        device_class = state.attributes.get("device_class")
        return device_class is None or isinstance(device_class, str)

    @staticmethod
    def extract(state: HaeoForecastState) -> tuple[Sequence[tuple[int, float]], str, SensorDeviceClass | None]:
        """Extract forecast data from HAEO forecast format.

        Returns:
            Tuple of (forecast_data, unit, device_class) where unit and device_class
            are derived from the entity state attributes.

        """
        parsed: list[tuple[int, float]] = [
            (parse_datetime_to_timestamp(time), float(value)) for time, value in state.attributes["forecast"].items()
        ]
        parsed.sort(key=lambda x: x[0])

        unit = state.attributes["unit_of_measurement"]

        device_class_attr = state.attributes.get("device_class")
        device_class: SensorDeviceClass | None = (
            SensorDeviceClass(device_class_attr) if device_class_attr else None
        )

        return parsed, unit, device_class
