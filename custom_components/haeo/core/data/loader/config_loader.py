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
from custom_components.haeo.core.schema import SchemaValue
from custom_components.haeo.core.schema.constant_value import is_constant_value
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS, ElementConfigData, ElementConfigSchema
from custom_components.haeo.core.schema.entity_value import is_entity_value
from custom_components.haeo.core.schema.field_hints import (
    FieldHint,
    ListFieldHints,
    extract_field_hints,
    extract_list_field_hints,
)
from custom_components.haeo.core.schema.none_value import is_none_value
from custom_components.haeo.core.state import StateMachine

from .sensor_loader import load_sensors

_PERCENT_OUTPUT_TYPES = frozenset({OutputType.STATE_OF_CHARGE, OutputType.EFFICIENCY})


def load_element_config(
    element_name: str,
    element_config: ElementConfigSchema,
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
        key: dict(value) if isinstance(value, Mapping) else value for key, value in element_config.items()
    }
    loaded[CONF_NAME] = element_name

    for section_name, section_fields in field_hints.items():
        section_config = element_config.get(section_name)
        if not isinstance(section_config, Mapping):
            continue

        for field_name, hint in section_fields.items():
            value = section_config.get(field_name)
            if value is None:
                if (default := _default_for_hint(hint, forecast_times)) is not _REMOVE:
                    loaded.setdefault(section_name, {})[field_name] = default
                continue

            resolved = resolve_field(value, hint, sm, forecast_times)
            if resolved is _REMOVE:
                if (default := _default_for_hint(hint, forecast_times)) is not _REMOVE:
                    loaded.setdefault(section_name, {})[field_name] = default
                else:
                    loaded_section = loaded.get(section_name)
                    if isinstance(loaded_section, dict):
                        loaded_section.pop(field_name, None)
            elif resolved is None and (default := _default_for_hint(hint, forecast_times)) is not _REMOVE:
                loaded.setdefault(section_name, {})[field_name] = default
            else:
                loaded.setdefault(section_name, {})[field_name] = resolved

    # Resolve list-based input fields (e.g. policy rules with entity prices)
    list_hints = extract_list_field_hints(ELEMENT_CONFIG_SCHEMAS[element_type])
    for list_key, hints in list_hints.items():
        items = element_config.get(list_key)
        if not isinstance(items, (list, tuple)):
            continue
        loaded_items = _resolve_list_items(items, hints, sm, forecast_times)
        loaded[list_key] = loaded_items

    return loaded  # type: ignore[return-value]


def load_element_configs(
    participants: Mapping[str, ElementConfigSchema],
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


def load_element_config_from_values(
    element_name: str,
    element_config: ElementConfigSchema,
    field_values: Mapping[tuple[str, ...], Any],
    forecast_times: Sequence[float],
) -> ElementConfigData:
    """Assemble an element's loaded config from pre-resolved input field values.

    This is the store-driven counterpart to :func:`load_element_config`. Instead
    of resolving each field against a state machine, it substitutes values that
    have already been resolved by ``InputStore`` instances, keyed by field path
    (``(section, field)`` or ``(list_key, index, field)``). Fields without an
    entry are treated as disabled and fall back to the same default/remove logic
    as the state-machine loader. No state machine is consulted.

    Args:
        element_name: Display name for the element.
        element_config: Raw element config dict (sectioned format).
        field_values: Map of field path to its resolved value.
        forecast_times: Boundary timestamps (used only for type-driven defaults).

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
        key: dict(value) if isinstance(value, Mapping) else value for key, value in element_config.items()
    }
    loaded[CONF_NAME] = element_name

    for section_name, section_fields in field_hints.items():
        for field_name, hint in section_fields.items():
            path = (section_name, field_name)
            default = _default_for_hint(hint, forecast_times)

            if path in field_values:
                resolved = field_values[path]
                if resolved is None and default is not _REMOVE:
                    loaded.setdefault(section_name, {})[field_name] = default
                else:
                    loaded.setdefault(section_name, {})[field_name] = resolved
                continue

            # No store for this field: disabled/none or absent in config.
            if default is not _REMOVE:
                loaded.setdefault(section_name, {})[field_name] = default
            else:
                loaded_section = loaded.get(section_name)
                if isinstance(loaded_section, dict):
                    loaded_section.pop(field_name, None)

    list_hints = extract_list_field_hints(ELEMENT_CONFIG_SCHEMAS[element_type])
    for list_key, hints in list_hints.items():
        items = element_config.get(list_key)
        if not isinstance(items, (list, tuple)):
            continue
        loaded_items: list[Any] = []
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                loaded_items.append(item)
                continue
            loaded_item = dict(item)
            for field_name in hints.fields:
                path = (list_key, str(index), field_name)
                if path in field_values:
                    loaded_item[field_name] = field_values[path]
                else:
                    loaded_item.pop(field_name, None)
            loaded_items.append(loaded_item)
        loaded[list_key] = loaded_items

    return loaded  # type: ignore[return-value]


class _Sentinel:
    """Sentinel value indicating a field should be removed."""


_REMOVE = _Sentinel()


def _default_for_hint(hint: FieldHint, forecast_times: Sequence[float]) -> _Sentinel | float | np.ndarray:
    """Return a type-driven default value for optional fields."""
    if hint.output_type is not OutputType.EFFICIENCY:
        return _REMOVE
    return _resolve_numeric(100.0, hint, forecast_times, is_percent=True)


def resolve_field(
    value: SchemaValue | bool,  # noqa: FBT001 (bool is a valid schema field value from config flow)
    hint: FieldHint,
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> _Sentinel | bool | float | np.ndarray | None:
    """Resolve a single field value based on its schema type and hint metadata.

    Shared by the config loader (whole-element resolution) and ``InputStore``
    (single-field resolution) so both paths produce identical values.
    """
    if is_none_value(value):
        return _REMOVE

    if isinstance(value, bool):
        return value

    if is_constant_value(value):
        unwrapped: float | bool | Sequence[str] = value["value"]
    elif is_entity_value(value):
        unwrapped = value["value"]
    else:
        return None

    if isinstance(unwrapped, bool):
        return unwrapped

    is_percent = hint.output_type in _PERCENT_OUTPUT_TYPES

    if isinstance(unwrapped, (int, float)):
        return _resolve_numeric(float(unwrapped), hint, forecast_times, is_percent=is_percent)

    if not unwrapped:
        return None

    return _resolve_entities(unwrapped, hint, sm, forecast_times, is_percent=is_percent)


def is_percent_field(hint: FieldHint) -> bool:
    """Return True when a field's values are stored as percentages."""
    return hint.output_type in _PERCENT_OUTPUT_TYPES


def resolve_constant(
    value: float | bool,  # noqa: FBT001 (bool is a valid constant field value)
    hint: FieldHint,
    forecast_times: Sequence[float],
) -> bool | float | np.ndarray:
    """Resolve a bare constant value into its optimization form.

    Booleans pass through unchanged; numerics are percentage-converted and
    expanded into a scalar or time series array per the field hint. Shared by
    ``InputStore`` so editable values resolve identically to the config loader.
    """
    if isinstance(value, bool):
        return value
    return _resolve_numeric(float(value), hint, forecast_times, is_percent=is_percent_field(hint))


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


def _resolve_entities(
    entity_ids: Sequence[str],
    hint: FieldHint,
    sm: StateMachine,
    forecast_times: Sequence[float],
    *,
    is_percent: bool,
) -> float | np.ndarray | None:
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


def _resolve_list_items(
    items: Sequence[Any],
    hints: ListFieldHints,
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> list[Any]:
    """Resolve hinted fields within each item of a list config field.

    Non-mapping items are passed through unchanged, so the return type is
    ``list[Any]`` rather than ``list[dict[str, Any]]``.
    """
    loaded_items: list[Any] = []
    for item in items:
        if not isinstance(item, Mapping):
            loaded_items.append(item)
            continue
        loaded_item = dict(item)
        for field_name, hint in hints.fields.items():
            value = item.get(field_name)
            if value is None:
                continue
            resolved = resolve_field(value, hint, sm, forecast_times)
            if isinstance(resolved, _Sentinel):
                loaded_item.pop(field_name, None)
            elif resolved is not None:
                loaded_item[field_name] = resolved
            else:
                loaded_item[field_name] = None
        loaded_items.append(loaded_item)
    return loaded_items


__all__ = [
    "is_percent_field",
    "load_element_config",
    "load_element_config_from_values",
    "load_element_configs",
    "resolve_constant",
    "resolve_field",
]
