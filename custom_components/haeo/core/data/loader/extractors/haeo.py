"""HAEO forecast parser.

Parses forecast data from HAEO's own output format, which uses a "forecast"
attribute containing a mapping of datetime keys to float values.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime, tzinfo
from enum import StrEnum
from itertools import pairwise
import logging
from typing import Literal, NotRequired, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import hold_until_next, is_parsable_to_datetime, parse_datetime_to_timestamp, step_points

_LOGGER = logging.getLogger(__name__)

Format = Literal["haeo"]
DOMAIN: Format = "haeo"


class InterpolationMode(StrEnum):
    """How a HAEO-format forecast's value varies between its points.

    Published as the ``interpolation_mode`` attribute beside ``forecast``.
    """

    LINEAR = "linear"
    """Values ramp linearly from one point to the next."""
    PREVIOUS = "previous"
    """Each value holds until the next point, and the last for as long as the step before it."""
    NEXT = "next"
    """Each value holds back to the previous point."""
    NEAREST = "nearest"
    """Each value holds to halfway between it and its neighbors."""


class HaeoForecastPoint(TypedDict):
    """Single point in a HAEO forecast time series."""

    time: str | datetime
    value: int | float


class HaeoForecastAttributes(TypedDict):
    """Type definition for HAEO forecast State attributes."""

    forecast: Sequence[HaeoForecastPoint]
    unit_of_measurement: str
    device_class: NotRequired[str]
    interpolation_mode: NotRequired[str]


class HaeoForecastState(Protocol):
    """Protocol for a State object with validated HAEO forecast data."""

    attributes: HaeoForecastAttributes


class Parser:
    """Parser for HAEO forecast data.

    Unlike other parsers, this one derives unit and device_class from the
    entity state attributes rather than using hardcoded values.
    """

    DOMAIN: Format = DOMAIN

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[HaeoForecastState]:
        """Check if data matches HAEO forecast format and narrow type."""
        # Check for required forecast attribute
        if "forecast" not in state.attributes:
            return False

        forecast = state.attributes["forecast"]

        # Only support list format: list of {"time": ..., "value": ...} dicts
        if not isinstance(forecast, Sequence) or isinstance(forecast, str):
            return False

        if not forecast:
            return False

        # Validate all entries are dicts with time and value fields
        if not all(
            isinstance(item, Mapping)
            and "time" in item
            and "value" in item
            and is_parsable_to_datetime(item["time"])
            and isinstance(item["value"], (int, float))
            for item in forecast
        ):
            return False

        # Check for required unit_of_measurement
        unit = state.attributes.get("unit_of_measurement")
        if not isinstance(unit, str) or not unit:
            return False

        # device_class is optional, but if present must be a string
        device_class = state.attributes.get("device_class")
        return device_class is None or isinstance(device_class, str)

    @staticmethod
    def extract(
        state: HaeoForecastState,
        time_zone: tzinfo,
    ) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement | str, DeviceClass | None]:
        """Extract forecast data from HAEO forecast format.

        Expects list format: list of {"time": ..., "value": ...} dicts.

        Returns:
            Tuple of (forecast_data, unit, device_class) where unit and device_class
            are derived from the entity state attributes.

        """
        forecast = state.attributes["forecast"]

        # Parse list of {"time": ..., "value": ...} dicts
        parsed = [(parse_datetime_to_timestamp(item["time"], time_zone), float(item["value"])) for item in forecast]
        parsed.sort(key=lambda x: x[0])

        parsed = _apply_interpolation_mode(parsed, _interpolation_mode(state.attributes.get("interpolation_mode")))

        unit_attr = state.attributes["unit_of_measurement"]
        unit: UnitOfMeasurement | str = UnitOfMeasurement.of(unit_attr) or unit_attr

        device_class_attr = state.attributes.get("device_class")
        device_class = DeviceClass.of(device_class_attr)

        return parsed, unit, device_class


def _interpolation_mode(value: object) -> InterpolationMode:
    """Read an interpolation_mode attribute, taking a missing or unknown mode as linear."""
    try:
        return InterpolationMode(value)
    except ValueError:
        return InterpolationMode.LINEAR


def _apply_interpolation_mode(data: list[tuple[int, float]], mode: InterpolationMode) -> list[tuple[int, float]]:
    """Add the points that make linear interpolation follow the interpolation mode.

    Args:
        data: Sorted sequence of (timestamp, value) tuples
        mode: Interpolation mode to apply

    Returns:
        The series with points added at each transition, unchanged for linear mode.

    """
    if len(data) <= 1:
        return data

    match mode:
        case InterpolationMode.LINEAR:
            return data
        case InterpolationMode.PREVIOUS:
            return step_points(hold_until_next(data))
        case InterpolationMode.NEXT:
            return [data[0], *(point for (t1, _), (t2, v2) in pairwise(data) for point in ((t1, v2), (t2, v2)))]
        case InterpolationMode.NEAREST:
            return [
                data[0],
                *(
                    point
                    for (t1, v1), (t2, v2) in pairwise(data)
                    for point in (((t1 + t2) // 2, v1), ((t1 + t2) // 2, v2), (t2, v2))
                ),
            ]
