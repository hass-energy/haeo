"""Load sensor data from Home Assistant entities."""

from collections.abc import Sequence

from custom_components.haeo.core.data.util import SensorPayload
from custom_components.haeo.core.data.util.field_units import check_source_unit
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import StateMachine
from custom_components.haeo.core.units import UnitOfMeasurement

from .extractors import extract, extract_reading


def load_sensor(sm: StateMachine, entity_id: str, *, output_type: OutputType | None = None) -> SensorPayload | None:
    """Load sensor data for a single entity ID.

    Checks if the sensor is a forecast sensor and loads it using forecast extraction,
    or falls back to the state value if no forecast is available.

    Args:
        sm: State machine implementation
        entity_id: The entity ID to load
        output_type: The input's output type, whose unit the sensor's unit must
            convert to. Not checked when None.

    Returns:
        Either a float (for simple values) or a list of (timestamp, value) tuples
        (for forecast data), or None if no data is available

    Raises:
        InputError: If the sensor supplies a value the input cannot use, such as
            one in a unit that does not convert to the input's unit.

    """
    state = sm.get(entity_id)
    if state is None:
        return None
    try:
        extracted = extract(state, time_zone=sm.time_zone, output_type=output_type)
    except ValueError:
        return None
    _check_unit(extracted.unit, output_type)
    return extracted.data


def load_reading(sm: StateMachine, entity_id: str, *, output_type: OutputType | None = None) -> float | None:
    """Load a sensor's reading for now, its state, whatever forecast it also carries.

    Args:
        sm: State machine implementation
        entity_id: The entity ID to load
        output_type: The input's output type, whose unit the sensor's unit must
            convert to. Not checked when None.

    Returns:
        The reading in base units, or None when the sensor is missing or its
        state is not a reading.

    Raises:
        InputError: If the sensor's unit does not convert to the input's unit.

    """
    state = sm.get(entity_id)
    if state is None:
        return None
    try:
        reading = extract_reading(state)
    except ValueError:
        return None
    _check_unit(reading.unit, output_type)
    return reading.data


def _check_unit(unit: UnitOfMeasurement | str | None, output_type: OutputType | None) -> None:
    """Check a sensor's unit converts to the input's unit, when the input's output type is given."""
    if output_type is not None:
        check_source_unit(None if unit is None else str(unit), output_type)


def load_sensors(
    sm: StateMachine, entity_ids: Sequence[str], *, output_type: OutputType | None = None
) -> dict[str, SensorPayload] | None:
    """Load sensor data for multiple entity IDs.

    An input built from several sensors is only meaningful with all of them,
    so one sensor without data makes the whole set unavailable, the same as
    when a single sensor is unavailable. Every sensor is still loaded first,
    so a sensor in an unusable unit is reported whatever its position.

    Args:
        sm: State machine implementation
        entity_ids: List of entity IDs to load
        output_type: The input's output type, whose unit each sensor's unit must
            convert to. Not checked when None.

    Returns:
        Dictionary mapping entity IDs to their sensor payloads, or None if there
        are no entity IDs or any sensor is missing or has no data.

    Raises:
        InputError: If any sensor supplies a value the input cannot use.

    """
    payloads = {entity_id: load_sensor(sm, entity_id, output_type=output_type) for entity_id in entity_ids}
    if not payloads or None in payloads.values():
        return None
    return {entity_id: payload for entity_id, payload in payloads.items() if payload is not None}


def load_readings(
    sm: StateMachine, entity_ids: Sequence[str], *, output_type: OutputType | None = None
) -> dict[str, float] | None:
    """Load each sensor's reading for now, or None when there are none or any sensor has none.

    Like :func:`load_sensors`, every sensor is loaded first, so a sensor in an
    unusable unit is reported whatever its position.

    Raises:
        InputError: If any sensor's unit does not convert to the input's unit.

    """
    readings = {entity_id: load_reading(sm, entity_id, output_type=output_type) for entity_id in entity_ids}
    if not readings or None in readings.values():
        return None
    return {entity_id: reading for entity_id, reading in readings.items() if reading is not None}
