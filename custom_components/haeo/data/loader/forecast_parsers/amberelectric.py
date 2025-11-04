"""Amber Electric (amberelectric) pricing forecast parser."""

from collections.abc import Sequence
from datetime import datetime
import logging
from typing import Any, Literal

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State
from homeassistant.util.dt import as_utc

_LOGGER = logging.getLogger(__name__)

Format = Literal["amberelectric"]
DOMAIN: Format = "amberelectric"


def _is_datetime_string(value: Any) -> bool:
    """Check if a value is a datetime instance."""
    if not isinstance(value, str):
        return False
    try:
        as_utc(datetime.fromisoformat(value))
        return True
    except ValueError:
        return False


class Parser:
    """Parser for Amber Electric pricing forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = "$/kWh"  # Amber Electric prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches Amber Electric (amberelectric) pricing format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            True if data matches amberelectric format, False otherwise

        """
        if not (isinstance(state.attributes, dict) and "forecasts" in state.attributes):
            return False

        forecasts = state.attributes["forecasts"]
        if not (isinstance(forecasts, list) and len(forecasts) > 0):
            return False

        return all(
            isinstance(item, dict)
            and {"start_time", "per_kwh"} <= item.keys()
            and isinstance(item["per_kwh"], (int, float))
            and _is_datetime_string(item["start_time"])
            for item in forecasts
        )

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from Amber Electric pricing format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            List of (timestamp_seconds, value) tuples sorted by timestamp

        """
        forecasts = state.attributes.get("forecasts", [])
        if not isinstance(forecasts, list):
            return []

        result = []
        for item in forecasts:
            if not isinstance(item, dict):
                continue

            start_time_str = item.get("start_time")
            per_kwh = item.get("per_kwh")

            if not start_time_str or per_kwh is None:
                continue

            try:
                # Parse ISO timestamp and convert to UTC
                dt = as_utc(datetime.fromisoformat(start_time_str))
                timestamp_seconds = int(dt.timestamp())
                value = float(per_kwh)
                result.append((timestamp_seconds, value))
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse Amber forecast item: %s", err)
                continue

        # Sort by timestamp
        result.sort(key=lambda x: x[0])
        return result
