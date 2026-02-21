"""Amber Electric energy pricing forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["amberelectric"]
DOMAIN: Format = "amberelectric"


class AmberForecastEntry(TypedDict):
    """Type definition for an Amber Electric forecast entry."""

    start_time: str | datetime
    end_time: str | datetime
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
    UNIT: UnitOfMeasurement = UnitOfMeasurement.DOLLAR_PER_KWH  # Amber Electric prices are in $/kWh
    DEVICE_CLASS: DeviceClass = DeviceClass.MONETARY

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[AmberElectricState]:
        """Check if data matches Amber Electric (amberelectric) pricing format and narrow type."""

        if "forecasts" not in state.attributes:
            return False

        forecasts = state.attributes["forecasts"]
        if not (isinstance(forecasts, Sequence) and not isinstance(forecasts, (str, bytes))) or not forecasts:
            return False

        return all(
            isinstance(item, Mapping)
            and "start_time" in item
            and "end_time" in item
            and "per_kwh" in item
            and isinstance(item["per_kwh"], (int, float))
            and is_parsable_to_datetime(item["start_time"])
            and is_parsable_to_datetime(item["end_time"])
            for item in forecasts
        )

    @staticmethod
    def _round_to_minute(timestamp: str | datetime) -> int:
        """Round timestamp to nearest minute (Amber provides times 1 second into each period)."""
        raw = parse_datetime_to_timestamp(timestamp)
        return int(round(raw / 60.0) * 60.0)

    @staticmethod
    def extract(state: AmberElectricState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Amber Electric pricing format.

        Emits boundary prices to create step functions: each window produces two points
        (start, price) and (end, price) to ensure constant pricing within the window
        without linear interpolation. Adjacent windows will have the same timestamp
        at boundaries to prevent interpolation.

        Returns timestamps in seconds as integers.
        """
        forecasts = list(state.attributes["forecasts"])
        parsed: list[tuple[int, float]] = []

        for item in forecasts:
            start = Parser._round_to_minute(item["start_time"])
            end = Parser._round_to_minute(item["end_time"])
            price = item["per_kwh"]

            # Emit start of window and end of window with same price
            parsed.append((start, price))
            parsed.append((end, price))

        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
