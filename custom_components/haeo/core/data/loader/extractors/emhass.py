"""EMHASS energy management forecast parser.

EMHASS (Energy Management for Home Assistant) provides forecasts with a unique format where:
- The attribute key varies by sensor type (forecasts, deferrables_schedule, etc.)
- Each forecast entry has a "date" timestamp field
- The value key matches the entity name (sensor.p_load_forecast → key "p_load_forecast")
- Values are stored as strings that need to be parsed to floats
"""

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

Format = Literal["emhass"]
DOMAIN: Format = "emhass"


class ForecastEntry(Protocol):
    """Protocol for an EMHASS forecast entry.

    Each entry has a "date" key and a dynamic value key matching the entity name.
    Values are typically numeric strings (e.g., "0.0", "-29322.0").
    """

    @property
    def date(self) -> str:
        """ISO8601 timestamp string."""
        ...

    def __getitem__(self, key: str) -> float | str:
        """Access value by entity name key."""
        ...


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
    attributes: Mapping[str, Sequence[ForecastEntry]]


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
    def _get_forecast_attribute(state: EntityState) -> Sequence[object] | None:
        """Find the forecast sequence from state attributes.

        Returns the first non-empty sequence attribute that matches an EMHASS forecast key.
        """
        for attr_key in FORECAST_ATTRIBUTE_KEYS:
            if attr_key not in state.attributes:
                continue
            forecast = state.attributes[attr_key]
            if isinstance(forecast, Sequence) and not isinstance(forecast, (str, bytes)) and forecast:
                return forecast
        return None

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[EmhassState]:
        """Check if data matches EMHASS forecast format."""
        forecast = Parser._get_forecast_attribute(state)
        if forecast is None:
            return False

        entity_name = Parser._get_entity_name(state.entity_id)
        return all(
            isinstance(item, Mapping)
            and "date" in item
            and entity_name in item
            and _is_numeric_or_numeric_string(item[entity_name])
            and is_parsable_to_datetime(item["date"])
            for item in forecast
        )

    @staticmethod
    def _get_forecast(state: EmhassState) -> Sequence[ForecastEntry]:
        """Get the forecast sequence from a validated EMHASS state.

        This must only be called after detect() returns True.
        """
        # detect() guarantees at least one forecast attribute exists
        return next(state.attributes[attr_key] for attr_key in FORECAST_ATTRIBUTE_KEYS if attr_key in state.attributes)

    @staticmethod
    def extract(
        state: EmhassState,
    ) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement | str | None, DeviceClass | None]:
        """Extract forecast data from EMHASS format.

        Returns: (parsed_data, unit, device_class)
        - unit and device_class are read from state attributes (EMHASS sets these)
        """
        entity_name = Parser._get_entity_name(state.entity_id)
        forecast = Parser._get_forecast(state)

        # detect() validated all items have date and entity_name keys
        parsed: list[tuple[int, float]] = [
            (
                parse_datetime_to_timestamp(item["date"]),
                _parse_numeric(item[entity_name]),
            )
            for item in forecast
        ]
        parsed.sort(key=lambda x: x[0])

        # Read unit and device_class from state attributes (EMHASS sets these)
        unit = state.attributes.get("unit_of_measurement")
        unit_str = str(unit) if unit is not None else None
        parsed_unit = UnitOfMeasurement.of(unit_str)

        device_class_attr = state.attributes.get("device_class")
        device_class = DeviceClass.of(device_class_attr)

        return parsed, parsed_unit or unit_str, device_class


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
