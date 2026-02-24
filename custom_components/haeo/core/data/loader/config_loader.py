"""Load element configurations by resolving schema values against a state machine.

This module provides the core data loading pipeline that resolves raw element
config schemas into fully loaded ElementConfigData ready for optimization.
It handles schema value dispatch (none/constant/entity), sensor loading,
forecast fusion, and unit conversion -- all without HA dependencies.
"""

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from custom_components.haeo.core.adapters.registry import is_element_type
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.core.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.constant_value import is_constant_value
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS, ElementConfigData
from custom_components.haeo.core.schema.entity_value import is_entity_value
from custom_components.haeo.core.schema.field_hints import FieldHint, extract_field_hints
from custom_components.haeo.core.schema.none_value import is_none_value
from custom_components.haeo.core.state import StateMachine

from .sensor_loader import load_sensors

_PERCENT_OUTPUT_TYPES = frozenset({OutputType.STATE_OF_CHARGE, OutputType.EFFICIENCY})


def load_element_config(
    element_name: str,
    element_config: Mapping[str, Any],
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> ElementConfigData:
    """Load a single element's config by resolving values against a state machine.

    Walks each field declared in the element's schema hints and resolves its
    value based on type:
    - none values: field is removed (disabled input)
    - constant values: scalar or expanded to time series array
    - entity values: loaded from state machine, combined, and fused to horizon

    Args:
        element_name: Display name for the element
        element_config: Raw element config dict (sectioned format)
        sm: State machine providing entity states
        forecast_times: Boundary timestamps (n+1 values defining n intervals)

    Returns:
        Loaded configuration with resolved time series and scalar values.

    Raises:
        ValueError: If element_type is unknown.

    """
    element_type = element_config.get(CONF_ELEMENT_TYPE)
    if not is_element_type(element_type):
        msg = f"Unknown element type: {element_type}"
        raise ValueError(msg)

    field_hints = extract_field_hints(ELEMENT_CONFIG_SCHEMAS[element_type])

    loaded: dict[str, Any] = {
        key: dict(value) if isinstance(value, dict) else value for key, value in element_config.items()
    }
    loaded[CONF_NAME] = element_name

    for section_name, section_fields in field_hints.items():
        section_config = element_config.get(section_name)
        if not isinstance(section_config, dict):
            continue

        for field_name, hint in section_fields.items():
            value = section_config.get(field_name)
            if value is None:
                continue

            resolved = _resolve_field(value, hint, sm, forecast_times)
            if resolved is _REMOVE:
                loaded_section = loaded.get(section_name)
                if isinstance(loaded_section, dict):
                    loaded_section.pop(field_name, None)
            else:
                loaded.setdefault(section_name, {})[field_name] = resolved

    return loaded  # type: ignore[return-value]


def load_element_configs(
    participants: Mapping[str, Mapping[str, Any]],
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> dict[str, ElementConfigData]:
    """Load all element configs by resolving values against a state machine.

    Args:
        participants: Map of element name to raw config dict
        sm: State machine providing entity states
        forecast_times: Boundary timestamps (n+1 values defining n intervals)

    Returns:
        Map of element name to loaded configuration.

    """
    return {name: load_element_config(name, config, sm, forecast_times) for name, config in participants.items()}


class _Sentinel:
    """Sentinel value indicating a field should be removed."""


_REMOVE = _Sentinel()


def _resolve_field(
    value: Any,
    hint: FieldHint,
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> Any:
    """Resolve a single field value based on its schema type and hint metadata."""
    if is_none_value(value):
        return _REMOVE

    if is_constant_value(value) or is_entity_value(value):
        value = value["value"]

    if isinstance(value, bool):
        return value

    is_percent = hint.output_type in _PERCENT_OUTPUT_TYPES

    if isinstance(value, (int, float)):
        return _resolve_numeric(float(value), hint, forecast_times, is_percent=is_percent)

    entity_ids = _extract_entity_ids(value)
    if not entity_ids:
        return value

    return _resolve_entities(entity_ids, hint, sm, forecast_times, is_percent=is_percent)


def _resolve_numeric(
    value: float,
    hint: FieldHint,
    forecast_times: Sequence[float],
    *,
    is_percent: bool,
) -> float | np.ndarray:
    """Expand a numeric constant into a scalar or time series array."""
    converted = value / 100.0 if is_percent else value

    if not hint.time_series:
        return converted

    count = len(forecast_times) if hint.boundaries else len(forecast_times) - 1
    return np.array([converted] * count)


def _extract_entity_ids(value: Any) -> list[str]:
    """Extract entity IDs from a raw value (string or list of strings)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def _resolve_entities(
    entity_ids: list[str],
    hint: FieldHint,
    sm: StateMachine,
    forecast_times: Sequence[float],
    *,
    is_percent: bool,
) -> Any:
    """Load entity data from state machine and fuse to horizon."""
    payloads = load_sensors(sm, entity_ids)
    if not payloads:
        return None

    present_value, forecast_series = combine_sensor_payloads(payloads)

    if not hint.time_series:
        scalar = present_value if present_value is not None else 0.0
        if is_percent:
            scalar /= 100.0
        return scalar

    if hint.boundaries:
        values = fuse_to_boundaries(present_value, forecast_series, list(forecast_times))
    else:
        values = fuse_to_intervals(present_value, forecast_series, list(forecast_times))

    if is_percent:
        values = [v / 100.0 for v in values]

    return np.array(values)


def extract_source_entity_ids(
    participants: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[str]]:
    """Extract source entity IDs from participant configs, grouped by element name.

    Walks each element's schema hints and collects entity IDs from entity-typed
    fields without loading any data. Used by the coordinator to subscribe
    directly to source sensor state changes.

    Args:
        participants: Map of element name to raw config dict

    Returns:
        Map of element name to list of source entity IDs. Elements with no
        entity-typed fields are omitted.

    """
    result: dict[str, list[str]] = {}
    for element_name, element_config in participants.items():
        element_type = element_config.get(CONF_ELEMENT_TYPE)
        if not is_element_type(element_type):
            continue

        field_hints = extract_field_hints(ELEMENT_CONFIG_SCHEMAS[element_type])
        entity_ids: list[str] = []

        for section_name, section_fields in field_hints.items():
            section_config = element_config.get(section_name)
            if not isinstance(section_config, dict):
                continue

            for field_name in section_fields:
                value = section_config.get(field_name)
                if value is None:
                    continue
                if is_entity_value(value):
                    entity_ids.extend(_extract_entity_ids(value["value"]))
                elif not is_constant_value(value) and not is_none_value(value):
                    entity_ids.extend(_extract_entity_ids(value))

        if entity_ids:
            result[element_name] = entity_ids

    return result


__all__ = [
    "extract_source_entity_ids",
    "load_element_config",
    "load_element_configs",
]
