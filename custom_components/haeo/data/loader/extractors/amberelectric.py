"""Amber Electric energy pricing forecast parser."""

from collections.abc import Sequence
import logging
from typing import Any, Literal

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from .utils.parse_datetime import parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["amberelectric"]
DOMAIN: Format = "amberelectric"


def _parse_entry(item: Any) -> tuple[int, float] | None:
    """Validate and convert a forecast item."""

    if not isinstance(item, dict):
        return None

    start_time = item.get("start_time")
    per_kwh = item.get("per_kwh")

    if start_time is None or per_kwh is None:
        return None

    try:
        timestamp_seconds = parse_datetime_to_timestamp(start_time)
        value = float(per_kwh)
    except (ValueError, TypeError):
        return None

    return timestamp_seconds, value


class Parser:
    """Parser for Amber Electric pricing forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = "$/kWh"  # Amber Electric prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches Amber Electric (amberelectric) pricing format."""

        if not (isinstance(state.attributes, dict) and "forecasts" in state.attributes):
            return False

        forecasts = state.attributes["forecasts"]
        if not (isinstance(forecasts, list) and forecasts):
            return False

        return all(_parse_entry(item) is not None for item in forecasts)

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from Amber Electric pricing format."""

        forecasts = state.attributes.get("forecasts")
        if not isinstance(forecasts, list) or not forecasts:
            _LOGGER.warning("Amber forecast payload is not a non-empty list; rejecting data")
            return []

        parsed: list[tuple[int, float]] = []
        for index, item in enumerate(forecasts):
            if (entry := _parse_entry(item)) is None:
                _LOGGER.warning("Invalid Amber forecast entry at index %s; rejecting entire dataset", index)
                return []
            parsed.append(entry)

        parsed.sort(key=lambda x: x[0])
        return parsed
