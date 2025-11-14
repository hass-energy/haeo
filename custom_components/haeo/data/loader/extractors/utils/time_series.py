"""Time series extraction utilities for forecast and sensor data."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

from custom_components.haeo.const import convert_to_base_unit

if TYPE_CHECKING:
    from custom_components.haeo.data.loader.extractors import ExtractorFormat

_LOGGER = logging.getLogger(__name__)

_INVALID_STATES: tuple[str, ...] = ("unknown", "unavailable", "none")


def detect_format(state: State) -> "ExtractorFormat | None":
    """Detect the forecast data format based on its structure.

    Args:
        state: The sensor state to analyze

    Returns:
        The detected format domain string, or None if no format detected

    """
    # Import here to avoid circular dependency
    from custom_components.haeo.data.loader.extractors import _FORMATS  # noqa: PLC0415

    valid_formats: list[ExtractorFormat] = [domain for domain, parser in _FORMATS.items() if parser.detect(state)]

    if len(valid_formats) == 1:
        return valid_formats[0]

    if len(valid_formats) > 1:
        _LOGGER.warning("Multiple forecast formats detected: %s", valid_formats)

    return None


def _extract_simple_value(state: State, *, entity_id: str) -> float:
    """Extract a simple numeric value from a state, converting to base units.

    Args:
        state: The sensor state
        entity_id: The entity ID for error messages

    Returns:
        The converted value in base units

    Raises:
        ValueError: If the state is unavailable or cannot be converted to a float

    """
    if state.state in _INVALID_STATES:
        msg = f"Sensor {entity_id} is unavailable"
        raise ValueError(msg)

    try:
        raw_value = float(state.state)
    except (TypeError, ValueError) as err:
        msg = f"Cannot parse sensor value for {entity_id}: {state.state}"
        raise ValueError(msg) from err

    device_class = state.attributes.get("device_class")
    unit = state.attributes.get("unit_of_measurement")

    return convert_to_base_unit(raw_value, unit, device_class)


def extract_time_series(state: State, *, entity_id: str) -> float | list[tuple[int, float]]:
    """Extract time series data from a sensor state.

    Attempts to parse the state as a forecast using known formats. If no format
    is detected, falls back to returning the state value as a single float.

    Args:
        state: The sensor state
        entity_id: The entity ID for error messages

    Returns:
        Either a float for simple values, or a list of (timestamp_seconds, value) tuples
        for forecast data sorted by timestamp.
        All values are converted to base units (kW for power, kWh for energy, etc.).

    Raises:
        ValueError: If the state cannot be parsed as either a forecast or simple value

    """
    # Import here to avoid circular dependency
    from custom_components.haeo.data.loader.extractors import _FORMATS  # noqa: PLC0415

    extractor_type = detect_format(state)

    if extractor_type is not None:
        extracted = _FORMATS[extractor_type].extract(state)
        if extracted:
            # Convert all forecast values to base units
            unit, device_class = get_extracted_units(state)
            return [(ts, convert_to_base_unit(value, unit, device_class)) for ts, value in extracted]

    return _extract_simple_value(state, entity_id=entity_id)


def get_extracted_units(state: State) -> tuple[str | None, SensorDeviceClass | None]:
    """Get the unit and device class for extracted data.

    Args:
        state: The sensor state

    Returns:
        Tuple of (unit, device_class) for the data. Returns state attributes if no format is detected.

    """
    # Import here to avoid circular dependency
    from custom_components.haeo.data.loader.extractors import _FORMATS  # noqa: PLC0415

    extractor_type = detect_format(state)

    if extractor_type is None:
        unit = state.attributes.get("unit_of_measurement")
        device_class = state.attributes.get("device_class")
        return (unit, device_class)

    extractor = _FORMATS[extractor_type]
    return extractor.UNIT, extractor.DEVICE_CLASS
