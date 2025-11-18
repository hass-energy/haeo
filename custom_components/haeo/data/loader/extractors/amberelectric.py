"""Amber Electric energy pricing forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from custom_components.haeo.helpers.types import is_sequence

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["amberelectric"]
DOMAIN: Format = "amberelectric"


class AmberForecastEntry(TypedDict):
    """Type definition for an Amber Electric forecast entry."""

    start_time: str | datetime
    per_kwh: float


class AmberElectricAttributes(TypedDict):
    """Type definition for Amber Electric State attributes."""

    forecasts: Sequence[AmberForecastEntry]


class AmberElectricState(Protocol):
    """Protocol for a State object with validated Amber Electric forecast data."""

    attributes: AmberElectricAttributes


class Parser:
    """Parser for Amber Electric pricing forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = "$/kWh"  # Amber Electric prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> TypeGuard[AmberElectricState]:
        """Check if data matches Amber Electric (amberelectric) pricing format and narrow type."""

        if "forecasts" not in state.attributes:
            return False

        forecasts = state.attributes["forecasts"]
        if not (is_sequence(forecasts) and not isinstance(forecasts, (str, bytes))) or not forecasts:
            return False

        return all(
            isinstance(item, Mapping)
            and "start_time" in item
            and "per_kwh" in item
            and isinstance(item["per_kwh"], (int, float))
            and is_parsable_to_datetime(item["start_time"])
            for item in forecasts
        )

    @staticmethod
    def extract(state: AmberElectricState) -> tuple[Sequence[tuple[int, float]], str, SensorDeviceClass]:
        """Extract forecast data from Amber Electric pricing format."""
        parsed: list[tuple[int, float]] = [
            (parse_datetime_to_timestamp(item["start_time"]), item["per_kwh"]) for item in state.attributes["forecasts"]
        ]
        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
