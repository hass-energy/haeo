"""Amber Electric energy pricing forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State
import numpy as np

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
        if not (isinstance(forecasts, Sequence) and not isinstance(forecasts, (str, bytes))) or not forecasts:
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
    def extract(state: AmberElectricState) -> tuple[Sequence[tuple[float, float]], str, SensorDeviceClass]:
        """Extract forecast data from Amber Electric pricing format.

        Emits boundary prices to create step functions: each window produces two points
        (start, price) and (nextafter(next_start, -inf), price) to ensure constant pricing
        within the window without linear interpolation.
        """
        forecasts = list(state.attributes["forecasts"])
        parsed: list[tuple[float, float]] = []

        for i, item in enumerate(forecasts):
            # Round start time to nearest minute (Amber provides times 1 second into each period)
            start = float(parse_datetime_to_timestamp(item["start_time"])) - 1.0
            price = item["per_kwh"]

            # Emit start of window
            parsed.append((start, price))

            # Determine end boundary (just before next window starts)
            if i + 1 < len(forecasts):
                # Use next window's start time (already rounded by the loop above)
                next_start = float(parse_datetime_to_timestamp(forecasts[i + 1]["start_time"])) - 1.0
            elif "end_time" in item:
                # Last window: use end_time + 1 second (to match Amber's pattern)
                next_start = float(parse_datetime_to_timestamp(item["end_time"]))
            else:
                # Fallback: use duration if available, else default to 30 minutes
                duration = item.get("duration", 30) * 60
                next_start = start + duration

            # Emit end of window (infinitesimally before next window)
            parsed.append((np.nextafter(next_start, -np.inf), price))

        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
