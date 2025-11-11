"""Solcast solar forecast parser."""

from collections.abc import Sequence
from datetime import datetime
import logging
from typing import Any, Literal

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import State
from homeassistant.util.dt import as_utc

_LOGGER = logging.getLogger(__name__)

Format = Literal["solcast_solar"]
DOMAIN: Format = "solcast_solar"


def _parse_entry(item: Any) -> tuple[int, float] | None:
    """Validate and convert a forecast item."""

    if not isinstance(item, dict):
        return None

    period_start_str = item.get("period_start")
    pv_estimate = item.get("pv_estimate")

    if not isinstance(period_start_str, (datetime, str)) or pv_estimate is None:
        return None

    try:
        dt = (
            as_utc(datetime.fromisoformat(period_start_str))
            if isinstance(period_start_str, str)
            else as_utc(period_start_str)
        )
        timestamp_seconds = int(dt.timestamp())
        value = float(pv_estimate)
    except (ValueError, TypeError):
        return None

    return timestamp_seconds, value


class Parser:
    """Parser for Solcast solar forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = UnitOfPower.KILO_WATT  # Solcast returns kW
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.POWER

    @staticmethod
    def detect(state: State) -> bool:
        """Check if data matches Solcast solar forecast format."""

        if not (isinstance(state.attributes, dict) and "detailedForecast" in state.attributes):
            return False

        detailed_forecast = state.attributes["detailedForecast"]
        if not (isinstance(detailed_forecast, list) and detailed_forecast):
            return False

        return all(_parse_entry(item) is not None for item in detailed_forecast)

    @staticmethod
    def extract(state: State) -> Sequence[tuple[int, float]]:
        """Extract forecast data from Solcast solar forecast format."""

        detailed_forecast = state.attributes.get("detailedForecast")
        if not isinstance(detailed_forecast, list) or not detailed_forecast:
            _LOGGER.warning("Solcast forecast payload is not a non-empty list; rejecting data")
            return []

        parsed: list[tuple[int, float]] = []
        for index, item in enumerate(detailed_forecast):
            if (entry := _parse_entry(item)) is None:
                _LOGGER.warning("Invalid Solcast forecast entry at index %s; rejecting entire dataset", index)
                return []
            parsed.append(entry)

        parsed.sort(key=lambda x: x[0])
        return parsed
