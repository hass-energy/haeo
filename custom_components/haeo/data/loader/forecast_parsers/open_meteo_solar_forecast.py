"""Open-Meteo solar forecast parser."""

from collections.abc import Sequence
from datetime import datetime
import logging
from typing import Literal

from homeassistant.core import State
from homeassistant.util.dt import as_utc

_LOGGER = logging.getLogger(__name__)

Format = Literal["open_meteo_solar_forecast"]
DOMAIN: Format = "open_meteo_solar_forecast"


class Parser:
    """Parser for Open-Meteo solar forecast data."""

    DOMAIN: Format = DOMAIN

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches Open-Meteo solar forecast format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            True if data matches Open-Meteo format, False otherwise

        """
        # Check for watts attribute with timestamp keys (Open-Meteo format)
        if isinstance(state.attributes, dict) and "watts" in state.attributes:
            watts = state.attributes["watts"]
            if isinstance(watts, dict) and len(watts) > 0:
                first_key = next(iter(watts.keys()))
                try:
                    datetime.fromisoformat(first_key)
                except (ValueError, TypeError):
                    return False
                return True

        return False

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from Open-Meteo solar forecast format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            List of (timestamp_seconds, value) tuples sorted by timestamp

        """
        watts = state.attributes.get("watts", {})
        if not isinstance(watts, dict):
            return []

        result = []
        for time_str, power_value in watts.items():
            try:
                # Parse ISO timestamp and convert to UTC
                dt = as_utc(datetime.fromisoformat(time_str))
                timestamp_seconds = int(dt.timestamp())
                value = float(power_value)
                result.append((timestamp_seconds, value))
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse Open-Meteo forecast item '%s': %s", time_str, err)
                continue

        # Sort by timestamp
        result.sort(key=lambda x: x[0])
        return result
