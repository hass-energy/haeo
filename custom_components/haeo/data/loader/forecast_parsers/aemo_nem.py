"""AEMO energy market forecast parser."""

from collections.abc import Sequence
from datetime import datetime
import logging
from typing import Literal

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State
from homeassistant.util.dt import as_utc

_LOGGER = logging.getLogger(__name__)

Format = Literal["aemo_nem"]
DOMAIN: Format = "aemo_nem"


class Parser:
    """Parser for AEMO energy market forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = "$/kWh"  # AEMO prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches AEMO energy market format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            True if data matches AEMO format, False otherwise

        """
        if not (isinstance(state.attributes, dict) and "forecast" in state.attributes):
            return False

        forecast = state.attributes["forecast"]
        if not (isinstance(forecast, list) and len(forecast) > 0):
            return False

        # Check if any item has both start_time and price
        return any(isinstance(item, dict) and "start_time" in item and "price" in item for item in forecast)

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from AEMO energy market format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            List of (timestamp_seconds, value) tuples sorted by timestamp

        """
        forecast = state.attributes.get("forecast", [])
        if not isinstance(forecast, list):
            return []

        result = []
        for item in forecast:
            if not isinstance(item, dict):
                continue

            start_time_str = item.get("start_time")
            price = item.get("price")

            if not start_time_str or price is None:
                continue

            try:
                # Parse ISO timestamp and convert to UTC
                dt = as_utc(datetime.fromisoformat(start_time_str))
                timestamp_seconds = int(dt.timestamp())
                value = float(price)
                result.append((timestamp_seconds, value))
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse AEMO forecast item: %s", err)
                continue

        # Sort by timestamp
        result.sort(key=lambda x: x[0])
        return result
