"""Shared utilities for building element config flow forms from input fields.

Every input field is an ``InputSelector``, which reports the field's value in
the form HAEO stores: an entity list, a constant, or none.
"""

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final  # noqa: TID251  # voluptuous schema dicts are Any by design

from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.data_entry_flow import section
import voluptuous as vol

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.model.const import ON_OFF_OUTPUT_TYPES
from custom_components.haeo.core.schema import (
    VALUE_TYPE_CONSTANT,
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    SchemaValue,
    as_constant_value,
    as_none_value,
    get_schema_value_kinds,
    is_none_value,
    is_schema_value,
)
from custom_components.haeo.elements.input_fields import (
    AnyInputFieldInfo,
    FieldSchemaInfo,
    InputFieldGroups,
    accepts_calendar_forecast,
    is_number_field_info,
    reads_calendar,
)
from custom_components.haeo.flows.input_selector import InputKind, InputSelector, InputSelectorConfig


@dataclass(frozen=True, slots=True)
class SectionDefinition:
    """Definition of a config flow section for grouping fields."""

    key: str
    fields: tuple[str, ...]
    collapsed: bool = False


# Domains an input's entities come from
_ENTITY_DOMAINS: Final = (DOMAIN, "sensor", "input_number", "number", "switch")


# Domains an on/off field also offers, as on/off states read as 1/0
# (e.g. an EV charger's plugged-in binary sensor)
_ON_OFF_DOMAINS: Final = ("binary_sensor", "input_boolean")


def entity_domains(field_info: AnyInputFieldInfo) -> list[str]:
    """Return the domains a field's entities come from.

    A field feeding calendar inputs offers only calendars, a forecast field
    also offers calendars read as forecasts, and an on/off field also offers
    on/off entities.
    """
    if reads_calendar(field_info):
        return [CALENDAR_DOMAIN]
    if accepts_calendar_forecast(field_info):
        return [*_ENTITY_DOMAINS, CALENDAR_DOMAIN]
    if field_info.output_type in ON_OFF_OUTPUT_TYPES:
        return [*_ENTITY_DOMAINS, *_ON_OFF_DOMAINS]
    return list(_ENTITY_DOMAINS)


def _get_nested_value(data: Mapping[str, object], field_name: str) -> object | None:
    """Find a field value in a nested mapping."""
    if field_name in data:
        return data[field_name]
    for value in data.values():
        if isinstance(value, Mapping):
            if field_name in value:
                return value[field_name]
            nested = _get_nested_value(value, field_name)
            if nested is not None:
                return nested
    return None


def input_kinds(field_schema: FieldSchemaInfo, field_info: AnyInputFieldInfo) -> list[InputKind]:
    """Return the kinds of value a field accepts, as the input selector offers them."""
    kinds = get_schema_value_kinds(field_schema.value_type)
    offered: list[InputKind] = []
    if VALUE_TYPE_ENTITY in kinds:
        offered.append(VALUE_TYPE_ENTITY)
    if VALUE_TYPE_CONSTANT in kinds:
        offered.append(VALUE_TYPE_CONSTANT)
    if VALUE_TYPE_NONE in kinds and not field_info.force_required:
        offered.append(VALUE_TYPE_NONE)
    return offered


def forecast_entities(entity_metadata: Iterable[EntityMetadata]) -> dict[str, tuple[float, ...]]:
    """Return the entities that carry a forecast, with each one's preview."""
    return {metadata.entity_id: metadata.preview for metadata in entity_metadata if metadata.forecast}


def reads_forecasts(field_info: AnyInputFieldInfo) -> bool:
    """Return whether a field feeds a time series input, which reads an entity's forecast instead of its state.

    A field with outputs feeds calendar inputs, which are always time series.
    """
    inputs = field_info.outputs.values() if field_info.outputs else (field_info,)
    return any(input_info.time_series for input_info in inputs)


def build_input_selector(
    field_info: AnyInputFieldInfo,
    *,
    kinds: Collection[InputKind],
    entities: Sequence[str] | None,
    forecasts: Mapping[str, Sequence[float]],
) -> InputSelector:
    """Build the input selector for a field.

    The field offers the entities in its domains, narrowed to ``entities`` when
    given. When the field reads forecasts, the config lists the offered entities
    that are in ``forecasts``, with their previews. A number
    field's constant takes the limits, step and unit of the field's number
    entity, so the form and the entity accept the same values.
    """
    domains = entity_domains(field_info)
    offered_forecasts: set[str] = set()
    if reads_forecasts(field_info):
        offered_forecasts = (
            set(forecasts).intersection(entities)
            if entities is not None
            else {entity_id for entity_id in forecasts if entity_id.split(".", 1)[0] in domains}
        )
    config: InputSelectorConfig = {
        "kinds": list(kinds),
        "value_type": "number" if is_number_field_info(field_info) else "boolean",
        "domains": domains,
        "forecasts": {entity_id: list(forecasts[entity_id]) for entity_id in sorted(offered_forecasts)},
    }
    if entities is not None:
        config["entities"] = list(entities)
    if is_number_field_info(field_info):
        description = field_info.entity_description
        if description.native_min_value is not None:
            config["min"] = description.native_min_value
        if description.native_max_value is not None:
            config["max"] = description.native_max_value
        if description.native_step:
            config["step"] = description.native_step
        if description.native_unit_of_measurement is not None:
            config["unit"] = description.native_unit_of_measurement
    return InputSelector(config)


def is_optional_input(field_schema: FieldSchemaInfo, field_info: AnyInputFieldInfo) -> bool:
    """Return whether a field may be left without a value."""
    return field_schema.is_optional and not field_info.force_required


def build_input_field_entries(
    input_fields: Mapping[str, AnyInputFieldInfo],
    *,
    field_schema: Mapping[str, FieldSchemaInfo],
    inclusion_map: Mapping[str, list[str]],
    forecasts: Mapping[str, Sequence[float]],
) -> dict[str, tuple[vol.Marker, InputSelector]]:
    """Build the schema entry of each input field."""
    entries: dict[str, tuple[vol.Marker, InputSelector]] = {}
    for field_info in input_fields.values():
        schema_info = field_schema.get(field_info.field_name)
        if schema_info is None:
            msg = f"Missing schema metadata for field '{field_info.field_name}'"
            raise RuntimeError(msg)
        marker = vol.Optional if is_optional_input(schema_info, field_info) else vol.Required
        entries[field_info.field_name] = (
            marker(field_info.field_name),
            build_input_selector(
                field_info,
                kinds=input_kinds(schema_info, field_info),
                entities=inclusion_map.get(field_info.field_name),
                forecasts=forecasts,
            ),
        )
    return entries


def build_section_schema(
    sections: Sequence[SectionDefinition],
    field_entries: Mapping[str, Mapping[str, tuple[vol.Marker, Any]]],
    *,
    top_level_entries: Mapping[str, tuple[vol.Marker, Any]] | None = None,
) -> dict[vol.Marker, Any]:
    """Build section-wrapped schema entries from a field entry map.

    Args:
        sections: Section definitions with field order.
        field_entries: Mapping of field_name -> (marker, selector).
        top_level_entries: Fields to place before sections, not wrapped in a section.

    Returns:
        Schema dict with top-level fields followed by sections.

    """
    schema_dict: dict[vol.Marker, Any] = {}

    if top_level_entries:
        schema_dict.update(dict(top_level_entries.values()))

    for section_def in sections:
        section_schema: dict[vol.Marker, Any] = {}
        section_entries = field_entries.get(section_def.key, {})
        for field_name in section_def.fields:
            entry = section_entries.get(field_name)
            if entry is None:
                continue
            marker, selector = entry
            section_schema[marker] = selector
        if section_schema:
            schema_dict[vol.Required(section_def.key)] = section(
                vol.Schema(section_schema),
                {"collapsed": section_def.collapsed},
            )

    return schema_dict


def build_sectioned_input_schema(
    sections: Sequence[SectionDefinition],
    input_fields: InputFieldGroups,
    field_schema: Mapping[str, Mapping[str, FieldSchemaInfo]],
    inclusion_map: Mapping[str, Mapping[str, list[str]]],
    *,
    forecasts: Mapping[str, Sequence[float]],
    extra_field_entries: Mapping[str, Mapping[str, tuple[vol.Marker, Any]]] | None = None,
    top_level_entries: Mapping[str, tuple[vol.Marker, Any]] | None = None,
) -> vol.Schema:
    """Build a sectioned schema with an input selector for each input field."""
    field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {
        key: dict(entries) for key, entries in (extra_field_entries or {}).items()
    }

    for section_def in sections:
        section_fields = input_fields.get(section_def.key, {})
        if not section_fields:
            continue
        field_entries.setdefault(section_def.key, {}).update(
            build_input_field_entries(
                section_fields,
                field_schema=field_schema.get(section_def.key, {}),
                inclusion_map=inclusion_map.get(section_def.key, {}),
                forecasts=forecasts,
            )
        )

    return vol.Schema(build_section_schema(sections, field_entries, top_level_entries=top_level_entries))


def get_input_default(
    field_info: AnyInputFieldInfo,
    current_data: Mapping[str, object] | None = None,
) -> SchemaValue:
    """Return the value a field's form opens with.

    An existing element's field opens with its stored value, and with none
    when nothing is stored, so saving the form unchanged changes nothing. A new
    element's field (no ``current_data``) opens with its default, else none.
    Every input opens with a value, as Home Assistant's form cannot start a
    required field of a selector it does not know without one.
    """
    if current_data is not None:
        current_value = _get_nested_value(current_data, field_info.field_name)
        return current_value if is_schema_value(current_value) else as_none_value()
    defaults = field_info.defaults
    if defaults is not None and defaults.mode == "value" and defaults.value is not None:
        return as_constant_value(defaults.value)
    return as_none_value()


def build_sectioned_input_defaults(
    sections: Sequence[SectionDefinition],
    input_fields: InputFieldGroups,
    *,
    current_data: Mapping[str, object] | None = None,
    base_defaults: Mapping[str, Mapping[str, object]] | None = None,
    exclude_fields: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    """Build the values each section's inputs open with."""
    defaults: dict[str, dict[str, object]] = {key: dict(values) for key, values in (base_defaults or {}).items()}

    for section_def in sections:
        section_defaults = defaults.setdefault(section_def.key, {})
        # An existing element's section opens with what it stores, even when it stores nothing
        current_section = current_data.get(section_def.key) if current_data is not None else None
        section_data = current_section if isinstance(current_section, Mapping) else None
        if current_data is not None and section_data is None:
            section_data = {}
        for field_info in input_fields.get(section_def.key, {}).values():
            if field_info.field_name in exclude_fields:
                continue
            section_defaults.setdefault(field_info.field_name, get_input_default(field_info, section_data))

    return defaults


def has_input_value(value: object) -> bool:
    """Return whether a submitted input holds a value."""
    return is_schema_value(value) and not is_none_value(value)


def validate_input_fields(
    user_input: Mapping[str, object],
    input_fields: Mapping[str, AnyInputFieldInfo],
    field_schema: Mapping[str, FieldSchemaInfo],
    *,
    exclude_fields: Collection[str] = (),
) -> dict[str, str]:
    """Return a "required" error for each required field submitted without a value."""
    errors: dict[str, str] = {}
    for field_name, field_info in input_fields.items():
        if field_name in exclude_fields:
            continue
        schema_info = field_schema.get(field_name)
        if schema_info is None:
            msg = f"Missing schema metadata for field '{field_name}'"
            raise RuntimeError(msg)
        if not is_optional_input(schema_info, field_info) and not has_input_value(user_input.get(field_name)):
            errors[field_name] = "required"
    return errors


def validate_sectioned_input_fields(
    user_input: Mapping[str, object],
    input_fields: InputFieldGroups,
    field_schema: Mapping[str, Mapping[str, FieldSchemaInfo]],
    sections: Sequence[SectionDefinition],
    *,
    exclude_fields: tuple[str, ...] = (),
) -> dict[str, str]:
    """Validate sectioned input fields.

    Errors are keyed by section because Home Assistant only shows errors for
    top-level form fields, so an error keyed by a field inside a section would
    re-show the form without telling the user why.
    """
    errors: dict[str, str] = {}
    for section_def in sections:
        section_input = user_input.get(section_def.key, {})
        if not isinstance(section_input, Mapping):
            continue
        section_errors = validate_input_fields(
            section_input,
            input_fields.get(section_def.key, {}),
            field_schema.get(section_def.key, {}),
            exclude_fields=exclude_fields,
        )
        if section_errors:
            errors[section_def.key] = next(iter(section_errors.values()))
    return errors


def convert_sectioned_input_to_config(
    user_input: Mapping[str, object],
    sections: Sequence[SectionDefinition],
    *,
    exclude_fields: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    """Return each section's submitted values as config, leaving out excluded fields.

    The input selectors have already validated their values into the stored form.
    """
    config: dict[str, dict[str, object]] = {}
    for section_def in sections:
        section_input = user_input.get(section_def.key, {})
        config[section_def.key] = (
            {key: value for key, value in section_input.items() if key not in exclude_fields}
            if isinstance(section_input, Mapping)
            else {}
        )
    return config


def as_mapping(value: object) -> Mapping[str, object]:
    """Narrow a stored dict value to a mapping, defaulting to empty."""
    return value if isinstance(value, Mapping) else {}


def as_str(value: object) -> str | None:
    """Narrow a stored dict value to a string, or None if absent/invalid."""
    return value if isinstance(value, str) else None


__all__ = [
    "SectionDefinition",
    "as_mapping",
    "as_str",
    "build_input_field_entries",
    "build_input_selector",
    "build_section_schema",
    "build_sectioned_input_defaults",
    "build_sectioned_input_schema",
    "convert_sectioned_input_to_config",
    "entity_domains",
    "get_input_default",
    "has_input_value",
    "input_kinds",
    "is_optional_input",
    "validate_input_fields",
    "validate_sectioned_input_fields",
]
