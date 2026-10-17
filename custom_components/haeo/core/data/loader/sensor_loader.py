"""Load sensor data from Home Assistant entities."""

from collections.abc import Sequence
from typing import TypeGuard

from custom_components.haeo.core.data.util.field_units import check_source_unit
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import StateMachine

from .extractors import extract

type ForecastSeries = Sequence[tuple[float, float]]
type SensorPayload = float | ForecastSeries


def is_sensor_sequence(value: object) -> TypeGuard[Sequence[str]]:
    """Return True when *value* is a sequence of sensor entity IDs."""

    return (
        isinstance(value, Sequence)
        and not isinstance(value, (bytes, str))
        and all(isinstance(item, str) for item in value)
    )


def normalize_entity_ids(value: object) -> list[str]:
    """Return a list of entity IDs extracted from *value*.

    Accepts either a single entity ID or any sequence of entity IDs. Raises
    ``TypeError`` when the input does not describe sensor entities.
    """

    if isinstance(value, str):
        return [value]

    if is_sensor_sequence(value):
        return list(value)

    msg = "Value must be a sensor entity ID or a sequence of sensor entity IDs"
    raise TypeError(msg)


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
        extracted = extract(state, output_type=output_type)
    except ValueError:
        return None
    if output_type is not None:
        check_source_unit(None if extracted.unit is None else str(extracted.unit), output_type)
    return extracted.data


def load_sensors(
    sm: StateMachine, entity_ids: Sequence[str], *, output_type: OutputType | None = None
) -> dict[str, SensorPayload] | None:
    """Load sensor data for multiple entity IDs.

    An input built from several sensors is only meaningful with all of them,
    so one sensor without data makes the whole set unavailable, the same as
    when a single sensor is unavailable.

    Args:
        sm: State machine implementation
        entity_ids: List of entity IDs to load
        output_type: The input's output type, whose unit each sensor's unit must
            convert to. Not checked when None.

    Returns:
        Dictionary mapping entity IDs to their sensor payloads, or None if any
        sensor is missing or has no data.

    """
    payloads: dict[str, SensorPayload] = {}

    for entity_id in entity_ids:
        payload = load_sensor(sm, entity_id, output_type=output_type)
        if payload is None:
            return None
        payloads[entity_id] = payload

    return payloads
