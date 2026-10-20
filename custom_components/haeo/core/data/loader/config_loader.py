"""Load element configurations by resolving schema values against a state machine.

This module provides the core data loading pipeline that resolves raw element
config schemas into fully loaded ElementConfigData ready for optimization.
It handles schema value dispatch (none/constant/entity), sensor loading,
forecast fusion, and unit conversion -- all without HA dependencies.
"""

from collections.abc import Collection, Mapping, Sequence
from typing import NamedTuple

import numpy as np

from custom_components.haeo.core.adapters.registry import is_element_type
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.data.util.field_units import NON_NEGATIVE_OUTPUT_TYPES
from custom_components.haeo.core.data.util.forecast_combiner import fuse_sensor_payloads, split_sensor_payloads
from custom_components.haeo.core.data.util.input_values import enforce_non_negative
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import SchemaValue, as_constant_value, as_entity_value, is_schema_value
from custom_components.haeo.core.schema.constant_value import is_constant_value
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS, ElementConfigData, ElementConfigSchema
from custom_components.haeo.core.schema.entity_value import is_entity_value
from custom_components.haeo.core.schema.field_hints import (
    FieldHint,
    extract_field_hints,
    extract_list_field_hints,
    field_inputs,
)
from custom_components.haeo.core.schema.none_value import is_none_value
from custom_components.haeo.core.schema.surfaced_policy import negated_price_paths
from custom_components.haeo.core.schema.util import get_nested_config_value_by_path
from custom_components.haeo.core.state import StateMachine

from .calendar_resolver import resolve_calendar
from .meter import resolve_meter
from .sensor_loader import load_sensors
from .switch import resolve_switch

_PERCENT_OUTPUT_TYPES = frozenset({OutputType.STATE_OF_CHARGE, OutputType.EFFICIENCY})

type InputPath = tuple[str, ...]


class ElementInput(NamedTuple):
    """One input of an element: where its value is loaded, where it is configured, and how it resolves."""

    path: InputPath
    config_path: InputPath
    hint: FieldHint


class InputsUnavailableError(ValueError):
    """Some configured inputs of an element have no data."""

    def __init__(self, element_name: str, paths: Sequence[InputPath]) -> None:
        """Record which inputs have no data."""
        self.paths = list(paths)
        super().__init__(f"Element '{element_name}' has unavailable inputs: {', '.join('.'.join(p) for p in paths)}")


def element_inputs(element_config: Mapping[str, object]) -> list[ElementInput]:
    """Return every input an element's config can feed, from its schema's field hints.

    Section fields give ``(section, field)`` paths. A field with ``outputs``
    gives one input per output, each reading the field's own config value.
    List fields give ``(list_key, index, field)`` paths for each mapping item.
    This is the one definition of an element's inputs, shared by the input
    stores at runtime and by offline loading.
    """
    element_type = element_config.get(CONF_ELEMENT_TYPE)
    if not is_element_type(element_type):
        return []
    schema_cls = ELEMENT_CONFIG_SCHEMAS[element_type]

    inputs: list[ElementInput] = []
    for section_name, section_fields in extract_field_hints(schema_cls).items():
        for field_name, field_hint in section_fields.items():
            config_path = (section_name, field_name)
            inputs.extend(
                ElementInput((section_name, input_name), config_path, hint)
                for input_name, hint in field_inputs(field_name, field_hint)
            )

    for list_key, list_hints in extract_list_field_hints(schema_cls).items():
        items = element_config.get(list_key)
        if not isinstance(items, (list, tuple)):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                continue
            for field_name, hint in list_hints.fields.items():
                path = (list_key, str(index), field_name)
                inputs.append(ElementInput(path, path, hint))

    return inputs


def configured_value(element_config: Mapping[str, object], config_path: InputPath) -> SchemaValue | bool | None:
    """Return the value configured for an input, or None when the input is absent or disabled.

    A bare number is a constant, as the input stores read it.
    """
    value = get_nested_config_value_by_path(element_config, config_path)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return as_constant_value(float(value))
    if is_schema_value(value) and not is_none_value(value):
        return value
    return None


def input_value(element_config: Mapping[str, object], element_input: ElementInput) -> SchemaValue | bool | None:
    """Return the value an input resolves from, or None when the input is absent or disabled.

    This is the input's configured value, except that a meter or switch
    input also reads the entities of its window calendar field, so its
    source states carry the calendar events it measures from.
    """
    value = configured_value(element_config, element_input.config_path)
    reads_since = element_input.hint.meter or element_input.hint.switch
    if reads_since is None or not is_entity_value(value):
        return value
    window = configured_value(element_config, (*element_input.config_path[:-1], reads_since.since))
    calendars = list(window["value"]) if is_entity_value(window) else []
    return as_entity_value([*value["value"], *calendars])


def load_element_config(
    element_name: str,
    element_config: ElementConfigSchema,
    sm: StateMachine,
    forecast_times: Sequence[float],
    *,
    negated_paths: Collection[InputPath] = frozenset(),
) -> ElementConfigData:
    """Load a single element's config by resolving its inputs against a state machine.

    Each configured input resolves through :func:`resolve_field`, as an input
    store does at runtime, and the values assemble through
    :func:`load_element_config_from_values`, as the coordinator does.

    Args:
        element_name: Display name for the element
        element_config: Raw element config dict (sectioned format)
        sm: State machine providing entity states
        forecast_times: Boundary timestamps (n+1 values defining n intervals)
        negated_paths: Input paths whose entity-driven values are negated, as
            returned by ``negated_price_paths`` for this element

    Returns:
        Loaded configuration with resolved time series and scalar values.

    Raises:
        ValueError: If element_type is unknown.
        InputsUnavailableError: If any configured input has no data, which
            stops an optimization at runtime too.
        InputError: If a source supplies a value an input cannot use.

    """
    field_values: dict[InputPath, bool | float | np.ndarray] = {}
    unavailable: list[InputPath] = []
    for element_input in element_inputs(element_config):
        value = input_value(element_config, element_input)
        if value is None:
            continue
        resolved = resolve_field(
            value, element_input.hint, sm, forecast_times, negate=element_input.path in negated_paths
        )
        if isinstance(resolved, (bool, float, int, np.ndarray)):
            field_values[element_input.path] = resolved
        else:
            unavailable.append(element_input.path)

    if unavailable:
        raise InputsUnavailableError(element_name, unavailable)

    return load_element_config_from_values(element_name, element_config, field_values, forecast_times)


def load_element_configs(
    participants: Mapping[str, ElementConfigSchema],
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> dict[str, ElementConfigData]:
    """Load all element configs by resolving values against a state machine.

    Entity-driven policy prices that surface a negated element price are
    negated, matching the input stores used at runtime.

    Args:
        participants: Map of element name to raw config dict
        sm: State machine providing entity states
        forecast_times: Boundary timestamps (n+1 values defining n intervals)

    Returns:
        Map of element name to loaded configuration.

    """
    negated = negated_price_paths(participants)
    return {
        name: load_element_config(name, config, sm, forecast_times, negated_paths=negated.get(name, frozenset()))
        for name, config in participants.items()
    }


def load_element_config_from_values(
    element_name: str,
    element_config: ElementConfigSchema,
    field_values: Mapping[tuple[str, ...], bool | float | np.ndarray | None],
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

    loaded: dict[str, object] = {
        key: dict(value) if isinstance(value, Mapping) else value for key, value in element_config.items()
    }
    loaded[CONF_NAME] = element_name

    for section_name, section_fields in field_hints.items():
        for field_name, field_hint in section_fields.items():
            if field_hint.outputs:
                _section_dict(loaded, section_name).pop(field_name, None)
            for input_name, hint in field_inputs(field_name, field_hint):
                path = (section_name, input_name)
                default = _default_for_hint(hint, forecast_times)

                if path in field_values:
                    resolved = field_values[path]
                    if resolved is None and default is not _REMOVE:
                        _section_dict(loaded, section_name)[input_name] = default
                    else:
                        _section_dict(loaded, section_name)[input_name] = resolved
                    continue

                # No store for this input: disabled/none or absent in config.
                if default is not _REMOVE:
                    _section_dict(loaded, section_name)[input_name] = default
                else:
                    loaded_section = loaded.get(section_name)
                    if isinstance(loaded_section, dict):
                        loaded_section.pop(input_name, None)

    list_hints = extract_list_field_hints(ELEMENT_CONFIG_SCHEMAS[element_type])
    for list_key, hints in list_hints.items():
        items = element_config.get(list_key)
        if not isinstance(items, (list, tuple)):
            continue
        loaded_items: list[object] = []
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


def _section_dict(loaded: dict[str, object], section_name: str) -> dict[str, object]:
    """Return the mutable dict for a config section, creating an empty one if absent.

    Sections already present in ``loaded`` are always dicts by construction --
    mappings in the raw config are copied via ``dict()`` before this is called --
    so the isinstance check only guards the first-write path for a new section.
    """
    section = loaded.setdefault(section_name, {})
    if not isinstance(section, dict):
        section = {}
        loaded[section_name] = section
    return section


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
    *,
    negate: bool = False,
) -> _Sentinel | bool | float | np.ndarray | None:
    """Resolve a single field value based on its schema type and hint metadata.

    Shared by the config loader (whole-element resolution) and ``InputStore``
    (single-field resolution) so both paths produce identical values.

    When ``negate`` is True, values resolved from entities are negated.
    Constant values are already stored negated, so they pass through unchanged.
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

    if hint.calendar is not None:
        return resolve_calendar(unwrapped, hint.calendar, hint.output_type, sm, forecast_times)

    if hint.meter is not None:
        return resolve_meter(unwrapped, hint.output_type, sm, forecast_times)

    if hint.switch is not None:
        return resolve_switch(unwrapped, sm, forecast_times)

    resolved = _resolve_entities(unwrapped, hint, sm, forecast_times, is_percent=is_percent)
    if negate and resolved is not None:
        return -resolved
    return resolved


def is_percent_field(hint: FieldHint) -> bool:
    """Return True when a field's values are stored as percentages."""
    return hint.output_type in _PERCENT_OUTPUT_TYPES


def _is_non_negative_field(hint: FieldHint) -> bool:
    """Return True when a field cannot be negative: a physical quantity, or a field whose minimum is zero or more.

    Deciding from the hint means runtime input stores and offline loading
    (diagnostics, simulation, scenarios) treat the same values the same way.
    """
    return hint.output_type in NON_NEGATIVE_OUTPUT_TYPES or (hint.min_value is not None and hint.min_value >= 0)


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
    payloads = load_sensors(sm, entity_ids, output_type=hint.output_type)
    if payloads is None:
        return None

    present_value, forecast_series = split_sensor_payloads(payloads)

    if not hint.time_series:
        raw = [present_value if present_value is not None else 0.0]
    else:
        raw = fuse_sensor_payloads(present_value, forecast_series, list(forecast_times), boundaries=hint.boundaries)

    values = np.array(raw, dtype=np.float64)
    if _is_non_negative_field(hint):
        values = enforce_non_negative(values)

    if is_percent:
        values = values / 100.0

    return values if hint.time_series else float(values[0])


__all__ = [
    "ElementInput",
    "InputsUnavailableError",
    "configured_value",
    "element_inputs",
    "input_value",
    "is_percent_field",
    "load_element_config",
    "load_element_config_from_values",
    "load_element_configs",
    "resolve_constant",
    "resolve_field",
]
