"""EMHASS energy management forecast parser.

EMHASS (Energy Management for Home Assistant) provides forecasts with a unique format where:
- The attribute key varies by sensor type (forecasts, deferrables_schedule, etc.)
- Each forecast entry has a "date" timestamp field
- The value key matches the entity name (sensor.p_load_forecast → key "p_load_forecast")
- Values are stored as strings that need to be parsed to floats
"""

from collections.abc import Mapping, Sequence
from datetime import tzinfo
from typing import Literal, Protocol, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import hold_until_next, is_parsable_to_datetime, parse_datetime_to_timestamp, period_means, step_points

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


type StepTiming = Literal["held", "mean", "start", "end"]
"""When in an optimization time step a value applies.

``held`` is constant across the step, as a schedule or price is. ``mean`` is
the mean of a smoothly varying quantity over the step, which best matches its
instantaneous value at the middle of the step. ``start`` and ``end`` are states
at the start or end of the step.
"""

# EMHASS uses different attribute keys for different sensor types. Every entry
# is dated at the start of its optimization time step. The forecasts attribute
# carries the optimizer's schedules (grid power, curtailment) as well as its PV
# and load forecasts, so it is held across each step as EMHASS models them all.
FORECAST_ATTRIBUTES: dict[str, StepTiming] = {
    "forecasts": "held",
    "deferrables_schedule": "held",
    "predicted_temperatures": "start",
    "battery_scheduled_power": "held",
    "battery_scheduled_soc": "end",
    "unit_load_cost_forecasts": "held",
    "unit_prod_price_forecasts": "held",
    "scheduled_forecast": "mean",
}


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
        for attr_key in FORECAST_ATTRIBUTES:
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
    def _get_forecast_key(state: EmhassState) -> str:
        """Get the attribute key holding the forecast of a validated EMHASS state.

        This must only be called after detect() returns True.
        """
        # detect() guarantees at least one forecast attribute exists
        return next(attr_key for attr_key in FORECAST_ATTRIBUTES if attr_key in state.attributes)

    @staticmethod
    def extract(
        state: EmhassState,
        time_zone: tzinfo,
    ) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement | str | None, DeviceClass | None]:
        """Extract forecast data from EMHASS format.

        Returns: (parsed_data, unit, device_class)
        - unit and device_class are read from state attributes (EMHASS sets these)

        Each step ends where the next starts, and the last lasts as long as the
        one before it. Schedules and prices hold across their step, so they
        become a step function. The ML forecaster's load forecast is a mean
        over its step, placed at the step's middle for the fuser to interpolate
        between. Battery state of charge is the state at the end of its step,
        and predicted temperature the state at its start.
        """
        entity_name = Parser._get_entity_name(state.entity_id)
        forecast_key = Parser._get_forecast_key(state)
        forecast = state.attributes[forecast_key]

        # detect() validated all items have date and entity_name keys
        parsed: list[tuple[int, float]] = [
            (
                parse_datetime_to_timestamp(item["date"], time_zone),
                _parse_numeric(item[entity_name]),
            )
            for item in forecast
        ]
        parsed = _apply_step_timing(parsed, FORECAST_ATTRIBUTES[forecast_key])

        # Read unit and device_class from state attributes (EMHASS sets these)
        unit = state.attributes.get("unit_of_measurement")
        unit_str = str(unit) if unit is not None else None
        parsed_unit = UnitOfMeasurement.of(unit_str)

        device_class_attr = state.attributes.get("device_class")
        device_class = DeviceClass.of(device_class_attr)

        return parsed, parsed_unit or unit_str, device_class


def _apply_step_timing(points: list[tuple[int, float]], timing: StepTiming) -> list[tuple[int, float]]:
    """Place values dated at the start of each step where they apply in time."""
    if len(points) < 2:  # noqa: PLR2004 (a step length needs two points, and one point is constant anyway)
        return points
    match timing:
        case "held":
            return step_points(hold_until_next(points))
        case "mean":
            return period_means(hold_until_next(points))
        case "start":
            return sorted(points)
        case "end":
            # The state at the first step's start is not published, so the first state holds back to it
            steps = hold_until_next(points)
            return [(steps[0][0], steps[0][2]), *((end, value) for _, end, value in steps)]


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
