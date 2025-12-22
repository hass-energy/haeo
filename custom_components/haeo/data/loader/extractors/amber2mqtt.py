"""Amber2MQTT energy pricing forecast parser.

This parser handles the amber2mqtt integration which provides Amber Electric
data via MQTT. Key differences from the official Amber Electric integration:
- Uses "Forecasts" (capitalized) instead of "forecasts" as the attribute key
- Feed-in sensors (detected by channel_type attribute) have negated per_kwh values
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["amber2mqtt"]
DOMAIN: Format = "amber2mqtt"


class Amber2MqttForecastEntry(TypedDict):
    """Type definition for an Amber2MQTT forecast entry."""

    start_time: str | datetime
    end_time: str | datetime
    per_kwh: float


class Amber2MqttAttributes(TypedDict):
    """Type definition for Amber2MQTT State attributes."""

    Forecasts: Sequence[Amber2MqttForecastEntry]
    channel_type: str


class Amber2MqttState(Protocol):
    """Protocol for a State object with validated Amber2MQTT forecast data."""

    entity_id: str
    attributes: Amber2MqttAttributes


class Parser:
    """Parser for Amber2MQTT pricing forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: str = "$/kWh"  # Amber Electric prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> TypeGuard[Amber2MqttState]:
        """Check if data matches Amber2MQTT pricing format and narrow type.

        Amber2MQTT uses "Forecasts" (capitalized) instead of "forecasts".
        """
        if "Forecasts" not in state.attributes:
            return False

        forecasts = state.attributes["Forecasts"]
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
        raw = float(parse_datetime_to_timestamp(timestamp))
        return int(round(raw / 60.0) * 60.0)

    @staticmethod
    def extract(state: Amber2MqttState) -> tuple[Sequence[tuple[int, float]], str, SensorDeviceClass]:
        """Extract forecast data from Amber2MQTT pricing format.

        Emits boundary prices to create step functions: each window produces two points
        (start, price) and (end, price) to ensure constant pricing within the window
        without linear interpolation. Adjacent windows will have the same timestamp
        at boundaries, which will be separated later to prevent interpolation.

        For feed-in sensors (detected by channel_type attribute), the per_kwh value is negated.

        Returns timestamps in seconds as integers.
        """
        forecasts = list(state.attributes["Forecasts"])
        parsed: list[tuple[int, float]] = []

        is_feedin = state.attributes.get("channel_type") == "feedin"

        for item in forecasts:
            start = Parser._round_to_minute(item["start_time"])
            end = Parser._round_to_minute(item["end_time"])
            price = -item["per_kwh"] if is_feedin else item["per_kwh"]

            # Emit start of window and end of window with same price
            parsed.append((start, price))
            parsed.append((end, price))

        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
