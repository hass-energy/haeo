"""Solcast solar forecast parser."""

from collections.abc import Sequence
from datetime import datetime
import logging
from typing import Literal

from homeassistant.core import State
from homeassistant.util.dt import as_utc

_LOGGER = logging.getLogger(__name__)

Format = Literal["solcast_solar"]
DOMAIN: Format = "solcast_solar"


class Parser:
    """Parser for Solcast solar forecast data."""

    DOMAIN: Format = DOMAIN

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches Solcast solar forecast format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            True if data matches Solcast format, False otherwise

        """
        if not (isinstance(state.attributes, dict) and "detailedForecast" in state.attributes):
            return False

        detailed_forecast = state.attributes["detailedForecast"]
        if not (isinstance(detailed_forecast, list) and len(detailed_forecast) > 0):
            return False

        # Check if any item has both period_start and pv_estimate
        return any(
            isinstance(item, dict) and "period_start" in item and "pv_estimate" in item for item in detailed_forecast
        )

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from Solcast solar forecast format.

        Args:
            state: The sensor state containing forecast data

        Returns:
            List of (timestamp_seconds, value) tuples sorted by timestamp

        """
        detailed_forecast = state.attributes.get("detailedForecast", [])
        if not isinstance(detailed_forecast, list):
            return []

        result = []
        for item in detailed_forecast:
            if not isinstance(item, dict):
                continue

            period_start_str = item.get("period_start")
            pv_estimate = item.get("pv_estimate")

            if not period_start_str or pv_estimate is None:
                continue

            try:
                # Parse ISO timestamp and convert to UTC
                dt = as_utc(datetime.fromisoformat(period_start_str))
                timestamp_seconds = int(dt.timestamp())
                value = float(pv_estimate)
                result.append((timestamp_seconds, value))
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse Solcast forecast item: %s", err)
                continue

        # Sort by timestamp
        result.sort(key=lambda x: x[0])
        return result
