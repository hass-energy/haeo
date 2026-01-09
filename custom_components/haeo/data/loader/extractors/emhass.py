"""EMHASS energy management forecast parser.

EMHASS (Energy Management for Home Assistant) provides forecasts with a unique format where:
- The attribute key varies by sensor type (forecasts, deferrables_schedule, etc.)
- Each forecast entry has a "date" timestamp field
- The value key matches the entity name (sensor.p_load_forecast → key "p_load_forecast")
- Values are stored as strings that need to be parsed to floats
"""

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

Format = Literal["emhass"]
DOMAIN: Format = "emhass"

# EMHASS uses different attribute keys for different sensor types
FORECAST_ATTRIBUTE_KEYS = (
    "forecasts",
    "deferrables_schedule",
    "predicted_temperatures",
    "battery_scheduled_power",
    "battery_scheduled_soc",
    "unit_load_cost_forecasts",
    "unit_prod_price_forecasts",
    "scheduled_forecast",
)


class EmhassState(Protocol):
    """Protocol for EMHASS State."""

    entity_id: str
    attributes: Mapping[str, object]


class Parser:
    """Parser for EMHASS forecast data."""

    DOMAIN: Format = DOMAIN

    @staticmethod
    def _get_entity_name(entity_id: str) -> str:
        """Extract entity name from entity_id.

        Example: 'sensor.p_load_forecast' -> 'p_load_forecast'
        """
        return entity_id.split(".", 1)[1] if "." in entity_id else entity_id

    @staticmethod
    def _find_forecast_data(
        state: State,
    ) -> tuple[Sequence[object], str, str] | None:
        """Find the forecast data, attribute key, and value key from state attributes.

        Returns: (forecast_list, attribute_key, value_key) or None if not found.
        Note: Only verifies the first item has the expected structure.
        Caller must validate all items.
        """
        entity_name = Parser._get_entity_name(state.entity_id)

        for attr_key in FORECAST_ATTRIBUTE_KEYS:
            if attr_key not in state.attributes:
                continue
            forecast = state.attributes[attr_key]
            if not isinstance(forecast, Sequence) or isinstance(forecast, (str, bytes)) or not forecast:
                continue
            # Check if first item has the entity_name as a key
            first_item = forecast[0]
            if isinstance(first_item, Mapping) and entity_name in first_item:
                return forecast, attr_key, entity_name
        return None

    @staticmethod
    def detect(state: State) -> TypeGuard[EmhassState]:
        """Check if data matches EMHASS forecast format."""
        result = Parser._find_forecast_data(state)
        if result is None:
            return False

        forecast, _, value_key = result
        return all(
            isinstance(item, Mapping)
            and "date" in item
            and value_key in item
            and _is_numeric_or_numeric_string(item[value_key])
            and is_parsable_to_datetime(item["date"])
            for item in forecast
        )

    @staticmethod
    def extract(
        state: EmhassState,
    ) -> tuple[Sequence[tuple[int, float]], str | None, SensorDeviceClass | None]:
        """Extract forecast data from EMHASS format.

        Returns: (parsed_data, unit, device_class)
        - unit and device_class are read from state attributes (EMHASS sets these)
        """
        result = Parser._find_forecast_data(state)  # type: ignore[arg-type]
        # detect() guarantees this is valid
        forecast, _, value_key = result  # type: ignore[misc]

        # detect() validated all items are Mapping with date and value_key
        parsed: list[tuple[int, float]] = [
            (
                parse_datetime_to_timestamp(item["date"]),  # type: ignore[index]
                _parse_numeric(item[value_key]),  # type: ignore[index]
            )
            for item in forecast
        ]
        parsed.sort(key=lambda x: x[0])

        # Read unit and device_class from state attributes (EMHASS sets these)
        unit = state.attributes.get("unit_of_measurement")
        unit_str = str(unit) if unit is not None else None

        device_class_attr = state.attributes.get("device_class")
        device_class = (
            SensorDeviceClass(device_class_attr)
            if device_class_attr and device_class_attr in SensorDeviceClass
            else None
        )

        return parsed, unit_str, device_class


def _is_numeric_or_numeric_string(value: object) -> bool:
    """Check if value is numeric or a string that can be parsed to float."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except ValueError:
            return False
    return False


def _parse_numeric(value: object) -> float:
    """Parse a numeric value or numeric string to float."""
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value))
