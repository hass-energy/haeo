"""Open-Meteo solar forecast parser."""

from collections.abc import Sequence
from datetime import datetime
import logging
from typing import Any, Literal

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import State
from homeassistant.util.dt import as_utc

_LOGGER = logging.getLogger(__name__)

Format = Literal["open_meteo_solar_forecast"]
DOMAIN: Format = "open_meteo_solar_forecast"


def _parse_entry(time_str: Any, power_value: Any) -> tuple[int, float] | None:
    """Validate and convert a forecast entry."""

    if not isinstance(time_str, str):
        return None

    try:
        dt = as_utc(datetime.fromisoformat(time_str))
        timestamp_seconds = int(dt.timestamp())
        value = float(power_value)
    except (ValueError, TypeError):
        return None

    return timestamp_seconds, value


class Parser:
    """Parser for Open-Meteo solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = UnitOfPower.WATT  # Data is in watts
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.POWER

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches Open-Meteo solar forecast format."""

        if not (isinstance(state.attributes, dict) and "watts" in state.attributes):
            return False

        watts = state.attributes["watts"]
        if not (isinstance(watts, dict) and watts):
            return False

        return all(_parse_entry(time_str, value) is not None for time_str, value in watts.items())

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from Open-Meteo solar forecast format."""

        watts = state.attributes.get("watts")
        if not isinstance(watts, dict) or not watts:
            _LOGGER.warning("Open-Meteo forecast payload is not a non-empty mapping; rejecting data")
            return []

        parsed: list[tuple[int, float]] = []
        for time_str, power_value in watts.items():
            if (entry := _parse_entry(time_str, power_value)) is None:
                _LOGGER.warning(
                    "Invalid Open-Meteo forecast entry at timestamp '%s'; rejecting entire dataset",
                    time_str,
                )
                return []
            parsed.append(entry)

        parsed.sort(key=lambda x: x[0])
        return parsed
