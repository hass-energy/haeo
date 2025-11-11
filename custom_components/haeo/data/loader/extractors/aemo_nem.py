"""AEMO energy market forecast parser."""

from collections.abc import Sequence
from datetime import datetime
import logging
from typing import Any, Literal

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State
from homeassistant.util.dt import as_utc

_LOGGER = logging.getLogger(__name__)

Format = Literal["aemo_nem"]
DOMAIN: Format = "aemo_nem"


def _parse_entry(item: Any) -> tuple[int, float] | None:
    """Validate and convert a forecast item."""

    if not isinstance(item, dict):
        return None

    start_time_str = item.get("start_time")
    price = item.get("price")

    if not isinstance(start_time_str, str) or price is None:
        return None

    try:
        dt = as_utc(datetime.fromisoformat(start_time_str))
        timestamp_seconds = int(dt.timestamp())
        value = float(price)
    except (ValueError, TypeError):
        return None

    return timestamp_seconds, value


class Parser:
    """Parser for AEMO energy market forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = "$/kWh"  # AEMO prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches AEMO energy market format."""

        if not (isinstance(state.attributes, dict) and "forecast" in state.attributes):
            return False

        forecast = state.attributes["forecast"]
        if not (isinstance(forecast, list) and forecast):
            return False

        return all(_parse_entry(item) is not None for item in forecast)

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from AEMO energy market format."""

        forecast = state.attributes.get("forecast")
        if not isinstance(forecast, list) or not forecast:
            _LOGGER.warning("AEMO forecast payload is not a non-empty list; rejecting data")
            return []

        parsed: list[tuple[int, float]] = []
        for index, item in enumerate(forecast):
            if (entry := _parse_entry(item)) is None:
                _LOGGER.warning("Invalid AEMO forecast entry at index %s; rejecting entire dataset", index)
                return []
            parsed.append(entry)

        parsed.sort(key=lambda x: x[0])
        return parsed
