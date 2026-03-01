"""Load sensor data from Home Assistant entities."""

from collections.abc import Sequence
from typing import Any, TypeGuard

from custom_components.haeo.core.state import StateMachine

from .extractors import extract

type ForecastSeries = Sequence[tuple[float, float]]
type SensorPayload = float | ForecastSeries


def is_sensor_sequence(value: Any) -> TypeGuard[Sequence[str]]:
    """Return True when *value* is a sequence of sensor entity IDs."""

    return (
        isinstance(value, Sequence)
        and not isinstance(value, (bytes, str))
        and all(isinstance(item, str) for item in value)
    )


def normalize_entity_ids(value: Any) -> list[str]:
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


def load_sensor(sm: StateMachine, entity_id: str) -> SensorPayload | None:
    """Load sensor data for a single entity ID.

    Checks if the sensor is a forecast sensor and loads it using forecast extraction,
    or falls back to the state value if no forecast is available.

    Args:
        sm: State machine implementation
        entity_id: The entity ID to load

    Returns:
        Either a float (for simple values) or a list of (timestamp, value) tuples
        (for forecast data), or None if no data is available

    """
    state = sm.get(entity_id)
    if state is None:
        return None

    try:
        return extract(state).data
    except ValueError:
        return None


def load_sensors(sm: StateMachine, entity_ids: Sequence[str]) -> dict[str, SensorPayload]:
    """Load sensor data for multiple entity IDs.

    Args:
        sm: State machine implementation
        entity_ids: List of entity IDs to load

    Returns:
        Dictionary mapping entity IDs to their sensor payloads.
        Only includes sensors that successfully loaded data.

    """
    payloads: dict[str, SensorPayload] = {}

    for entity_id in entity_ids:
        payload = load_sensor(sm, entity_id)
        if payload is not None:
            payloads[entity_id] = payload

    return payloads
