"""Shared utilities for building element config flows with choose selectors.

This module provides utilities for the unified config flow pattern using
Home Assistant's ChooseSelector, allowing users to pick between "Entity"
(select from compatible sensors) or "Constant" (enter a value directly).
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import async_get_hass
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    ChooseSelector,
    ChooseSelectorChoiceConfig,
    ChooseSelectorConfig,
    ConstantSelector,
    ConstantSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldGroups, InputFieldInfo
from custom_components.haeo.schema import (
    VALUE_TYPE_CONSTANT,
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    as_constant_value,
    as_entity_value,
    as_none_value,
    get_schema_value_kinds,
    is_constant_value,
    is_entity_value,
    is_none_value,
    is_schema_value,
    normalize_entity_ids,
)

# Choose selector choice keys (used for config flow data and translations)
CHOICE_ENTITY = VALUE_TYPE_ENTITY
CHOICE_CONSTANT = VALUE_TYPE_CONSTANT
CHOICE_NONE = VALUE_TYPE_NONE


@dataclass(frozen=True, slots=True)
class SectionDefinition:
    """Definition of a config flow section for grouping fields."""

    key: str
    fields: tuple[str, ...]
    collapsed: bool = False


def _get_nested_value(data: Mapping[str, Any], field_name: str) -> Any | None:
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


def number_selector_from_field(
    field_info: InputFieldInfo[NumberEntityDescription],
) -> NumberSelector:  # type: ignore[type-arg]
    """Build a NumberSelector from InputFieldInfo entity description.

    Reuses min/max/step/unit from the NumberEntityDescription to ensure
    consistency between config flow and number entities.

    Args:
        field_info: Input field metadata containing NumberEntityDescription.

    Returns:
        NumberSelector configured with the same constraints as the entity.

    """
    desc = field_info.entity_description

    # Build config, handling None values
    config_kwargs: dict[str, Any] = {
        "mode": NumberSelectorMode.BOX,
        "step": desc.native_step if desc.native_step else "any",
    }
    if desc.native_min_value is not None:
        config_kwargs["min"] = desc.native_min_value
    if desc.native_max_value is not None:
        config_kwargs["max"] = desc.native_max_value
    if desc.native_unit_of_measurement is not None:
        config_kwargs["unit_of_measurement"] = desc.native_unit_of_measurement

    return NumberSelector(NumberSelectorConfig(**config_kwargs))


def boolean_selector_from_field() -> BooleanSelector:  # type: ignore[type-arg]
    """Build a BooleanSelector.

    Returns:
        BooleanSelector for boolean field.

    """
    return BooleanSelector(BooleanSelectorConfig())


def get_haeo_input_entity_ids() -> list[str]:
    """Get all HAEO-created input entity IDs.

    Returns all entity IDs for HAEO input entities (number/switch) that were
    created for configurable fields. These should always be included in entity
    pickers so they can be re-selected during reconfiguration.

    Returns:
        List of entity IDs for HAEO input entities.

    """
    hass = async_get_hass()
    registry = er.async_get(hass)
    return [
        entry.entity_id
        for entry in registry.entities.values()
        if entry.platform == DOMAIN and entry.domain in ("number", "switch")
    ]


def resolve_haeo_input_entity_id(
    entry_id: str,
    subentry_id: str,
    field_name: str,
) -> str | None:
    """Resolve the HAEO-created entity for a configured field.

    When a user configures a field with a constant value, HAEO creates an
    input entity (e.g., number.grid_export_limit). This function looks up
    that resolved entity.

    Args:
        entry_id: The config entry ID.
        subentry_id: The subentry ID for the element.
        field_name: The field name (e.g., 'export_limit').

    Returns:
        The entity_id (e.g., 'number.grid_export_limit') or None if not found.

    """
    hass = async_get_hass()
    registry = er.async_get(hass)
    unique_id = f"{entry_id}_{subentry_id}_{field_name}"
    return registry.async_get_entity_id("number", DOMAIN, unique_id)


def build_entity_selector(
    *,
    include_entities: list[str] | None = None,
    multiple: bool = True,
) -> EntitySelector:  # type: ignore[type-arg]
    """Build an EntitySelector for compatible entities.

    Args:
        include_entities: Entity IDs to include (compatible entities from unit filtering).
        multiple: Whether to allow multiple entity selection (for chaining).

    Returns:
        EntitySelector configured with include_entities list.

    """
    # Start with compatible entities from unit filtering
    entities_to_include = list(include_entities or [])

    # Include all HAEO input entities so they can be re-selected during reconfigure
    entities_to_include.extend(get_haeo_input_entity_ids())

    config_kwargs: dict[str, Any] = {
        "domain": [DOMAIN, "sensor", "input_number", "number", "switch"],
        "multiple": multiple,
    }
    if entities_to_include:
        config_kwargs["include_entities"] = entities_to_include

    return EntitySelector(EntitySelectorConfig(**config_kwargs))


def _get_allowed_choices(field_schema: FieldSchemaInfo, field_info: InputFieldInfo[Any]) -> frozenset[str]:
    kinds = get_schema_value_kinds(field_schema.value_type)
    choices: set[str] = set()
    if VALUE_TYPE_ENTITY in kinds:
        choices.add(CHOICE_ENTITY)
    if VALUE_TYPE_CONSTANT in kinds:
        choices.add(CHOICE_CONSTANT)
    if VALUE_TYPE_NONE in kinds and not field_info.force_required:
        choices.add(CHOICE_NONE)
    return frozenset(choices)


def get_preferred_choice(
    field_info: InputFieldInfo[Any],
    current_data: Mapping[str, Any] | None = None,
    *,
    allowed_choices: Collection[str],
) -> str:
    """Determine which choice should be first in the ChooseSelector.

    The ChooseSelector always selects the first choice, so we order
    choices based on what should be pre-selected.
    """
    field_name = field_info.field_name
    choices = set(allowed_choices)

    # Reconfigure: infer from stored value
    if current_data is not None:
        value = _get_nested_value(current_data, field_name)
        if is_entity_value(value) and CHOICE_ENTITY in choices:
            return CHOICE_ENTITY
        if is_constant_value(value) and CHOICE_CONSTANT in choices:
            return CHOICE_CONSTANT
        if is_none_value(value) and CHOICE_NONE in choices:
            return CHOICE_NONE

    # New entry: check for explicit default mode
    if field_info.defaults is not None:
        if field_info.defaults.mode is None and CHOICE_NONE in choices:
            return CHOICE_NONE
        if field_info.defaults.mode:
            preferred = CHOICE_CONSTANT if field_info.defaults.mode == "value" else CHOICE_ENTITY
            if preferred in choices:
                return preferred

    if CHOICE_NONE in choices:
        return CHOICE_NONE
    if CHOICE_ENTITY in choices:
        return CHOICE_ENTITY
    if CHOICE_CONSTANT in choices:
        return CHOICE_CONSTANT
    return CHOICE_NONE


class NormalizingChooseSelector(ChooseSelector):  # type: ignore[type-arg]
    """ChooseSelector wrapper that normalizes raw dict format from frontend.

    Handles the case where frontend sends raw dict format like:
    {"active_choice": "none", "constant": 100}

    Converts to expected format before delegating to ChooseSelector.
    """

    def __call__(self, data: Any) -> Any:
        """Normalize data before validation."""
        normalized = self._normalize(data)
        return super().__call__(normalized)  # type: ignore[misc]

    def _normalize(self, value: Any) -> Any:
        """Normalize raw dict format to expected value."""
        if isinstance(value, dict) and "active_choice" in value:
            choice = value.get("active_choice")
            if choice == CHOICE_NONE:
                return ""  # ConstantSelector expects empty string
            if choice == CHOICE_ENTITY:
                return value.get(CHOICE_ENTITY, [])
            if choice == CHOICE_CONSTANT:
                return value.get(CHOICE_CONSTANT)
        return value


def build_choose_selector(
    field_info: InputFieldInfo[Any],
    *,
    allowed_choices: Collection[str],
    include_entities: list[str] | None = None,
    multiple: bool = True,
    preferred_choice: str = CHOICE_ENTITY,
) -> Any:
    """Build a ChooseSelector allowing user to pick Entity, Constant, or Disabled.

    Args:
        field_info: Input field metadata.
        allowed_choices: Choice keys allowed for this field.
        include_entities: Entity IDs to include (compatible entities from unit filtering).
        multiple: Whether to allow multiple entity selection (for chaining).
        preferred_choice: Which choice should appear first (will be pre-selected).

    Returns:
        ChooseSelector with Entity and Constant options (and Disabled for optional fields).

    Raises:
        RuntimeError: If ChooseSelector is not available (requires HA 2026.1+).

    """
    # Build entity selector for the "entity" choice
    entity_selector = build_entity_selector(
        include_entities=include_entities,
        multiple=multiple,
    )

    # Build value selector for the "constant" choice based on field type
    if type(field_info.entity_description).__name__ == "SwitchEntityDescription":
        value_selector = boolean_selector_from_field()
    else:
        value_selector = number_selector_from_field(field_info)  # type: ignore[arg-type]

    # Build choice configs - must use serialized dict format for ChooseSelector validation
    # The ChooseSelector's __call__ uses selector() which expects a dict, not Selector object
    entity_choice = ChooseSelectorChoiceConfig(selector=entity_selector.serialize()["selector"])
    constant_choice = ChooseSelectorChoiceConfig(selector=value_selector.serialize()["selector"])

    # Build ordered choices dict with preferred choice first
    # (ChooseSelector always selects the first option)
    choices: dict[str, ChooseSelectorChoiceConfig]
    choice_map: dict[str, ChooseSelectorChoiceConfig] = {}

    if CHOICE_ENTITY in allowed_choices:
        choice_map[CHOICE_ENTITY] = entity_choice
    if CHOICE_CONSTANT in allowed_choices:
        choice_map[CHOICE_CONSTANT] = constant_choice
    if CHOICE_NONE in allowed_choices:
        none_selector = ConstantSelector(ConstantSelectorConfig(value=""))
        choice_map[CHOICE_NONE] = ChooseSelectorChoiceConfig(selector=none_selector.serialize()["selector"])

    choice_order = [choice for choice in (CHOICE_ENTITY, CHOICE_CONSTANT, CHOICE_NONE) if choice in choice_map]

    if not choice_order:
        msg = f"No allowed choices for field '{field_info.field_name}'"
        raise RuntimeError(msg)

    # Move preferred choice to the start
    # Needed in HA version 2026.1.1, as it currently only supports providing a suggested value for the first choice.
    if preferred_choice in choice_order:
        choice_order.remove(preferred_choice)
        choice_order.insert(0, preferred_choice)

    choices = {k: choice_map[k] for k in choice_order}

    return NormalizingChooseSelector(
        ChooseSelectorConfig(
            choices=choices,
            translation_key="input_source",
        )
    )


def build_choose_schema_entry(
    field_info: InputFieldInfo[Any],
    *,
    is_optional: bool,
    allowed_choices: Collection[str],
    include_entities: list[str] | None = None,
    multiple: bool = True,
    preferred_choice: str = CHOICE_ENTITY,
) -> tuple[vol.Marker, Any]:
    """Build a schema entry using NormalizingChooseSelector.

    Args:
        field_info: Input field metadata.
        is_optional: Whether the field is optional (adds "none" choice).
        allowed_choices: Choice keys allowed for this field.
        include_entities: Entity IDs to include (compatible entities from unit filtering).
        multiple: Whether to allow multiple entity selection.
        preferred_choice: Which choice should appear first (will be pre-selected).

    Returns:
        Tuple of (vol.Required/Optional marker, NormalizingChooseSelector).

    """
    field_name = field_info.field_name
    selector = build_choose_selector(
        field_info,
        allowed_choices=allowed_choices,
        include_entities=include_entities,
        multiple=multiple,
        preferred_choice=preferred_choice,
    )

    if is_optional:
        return vol.Optional(field_name), selector
    return vol.Required(field_name), selector


def build_choose_field_entries(
    input_fields: Mapping[str, InputFieldInfo[Any]],
    *,
    field_schema: Mapping[str, FieldSchemaInfo],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build choose selector entries for input fields.

    Args:
        input_fields: Mapping of InputFieldInfo keyed by field name.
        field_schema: Mapping of field names to schema metadata.
        inclusion_map: Mapping of field name -> compatible entity IDs.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Mapping of field_name -> (marker, selector) for schema insertion.

    """
    entries: dict[str, tuple[vol.Marker, Any]] = {}

    for field_info in input_fields.values():
        schema_info = field_schema.get(field_info.field_name)
        if schema_info is None:
            msg = f"Missing schema metadata for field '{field_info.field_name}'"
            raise RuntimeError(msg)
        is_optional = schema_info.is_optional and not field_info.force_required
        allowed_choices = _get_allowed_choices(schema_info, field_info)
        include_entities = inclusion_map.get(field_info.field_name)
        preferred = get_preferred_choice(field_info, current_data, allowed_choices=allowed_choices)
        marker, selector = build_choose_schema_entry(
            field_info,
            is_optional=is_optional,
            allowed_choices=allowed_choices,
            include_entities=include_entities,
            preferred_choice=preferred,
        )
        entries[field_info.field_name] = (marker, selector)

    return entries


def build_section_schema(
    sections: Sequence[SectionDefinition],
    field_entries: Mapping[str, Mapping[str, tuple[vol.Marker, Any]]],
) -> dict[vol.Marker, Any]:
    """Build section-wrapped schema entries from a field entry map.

    Args:
        sections: Section definitions with field order.
        field_entries: Mapping of field_name -> (marker, selector).

    Returns:
        Schema dict with sections (data_entry_flow.section) in order.

    """
    schema_dict: dict[vol.Marker, Any] = {}

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


def flatten_section_input(
    user_input: dict[str, Any] | None,
    section_keys: Collection[str],
) -> dict[str, Any] | None:
    """Flatten sectioned user input into a flat dictionary.

    Args:
        user_input: User input from the form.
        section_keys: Keys used for section wrappers in the schema.

    Returns:
        Flattened user input, or None if input was None.

    """
    if user_input is None:
        return None

    result: dict[str, Any] = {}

    for key, value in user_input.items():
        if key in section_keys and isinstance(value, dict):
            result.update(value)
        else:
            result[key] = value

    return result


def nest_section_defaults(
    defaults: Mapping[str, Any],
    sections: Sequence[SectionDefinition],
) -> dict[str, Any]:
    """Nest flat defaults into sectioned defaults for the schema.

    Args:
        defaults: Flat mapping of field_name -> default value.
        sections: Section definitions with field membership.

    Returns:
        Defaults dict matching the sectioned schema shape.

    """
    result: dict[str, Any] = {}
    remaining: dict[str, Any] = dict(defaults)

    for section_def in sections:
        section_defaults: dict[str, Any] = {}
        for field_name in section_def.fields:
            if field_name in remaining:
                section_defaults[field_name] = remaining.pop(field_name)
        if section_defaults:
            result[section_def.key] = section_defaults

    result.update(remaining)
    return result


def preprocess_sectioned_choose_input(
    user_input: dict[str, Any] | None,
    input_fields: InputFieldGroups,
    sections: Sequence[SectionDefinition],
) -> dict[str, Any] | None:
    """Preprocess sectioned input to normalize ChooseSelector data."""
    if user_input is None:
        return None

    result: dict[str, Any] = dict(user_input)
    section_keys = {section.key for section in sections}
    if not section_keys.intersection(result):
        result = _nest_section_input(result, sections)

    for section_def in sections:
        section_input = result.get(section_def.key)
        if not isinstance(section_input, dict):
            continue
        section_fields = input_fields.get(section_def.key, {})
        normalized = preprocess_choose_selector_input(section_input, section_fields)
        result[section_def.key] = normalized or {}
    return result


def _nest_section_input(user_input: Mapping[str, Any], sections: Sequence[SectionDefinition]) -> dict[str, Any]:
    """Nest flat input into sectioned input based on section definitions."""
    result: dict[str, Any] = {section_def.key: {} for section_def in sections}
    for key, value in user_input.items():
        matched = False
        for section_def in sections:
            if key in section_def.fields:
                result[section_def.key][key] = value
                matched = True
                break
        if not matched:
            result[key] = value
    return result


def validate_sectioned_choose_fields(
    user_input: Mapping[str, Any],
    input_fields: InputFieldGroups,
    field_schema: Mapping[str, Mapping[str, FieldSchemaInfo]],
    sections: Sequence[SectionDefinition],
    *,
    exclude_fields: tuple[str, ...] = (),
) -> dict[str, str]:
    """Validate choose fields for sectioned input."""
    errors: dict[str, str] = {}
    for section_def in sections:
        section_input = user_input.get(section_def.key, {})
        if not isinstance(section_input, Mapping):
            continue
        section_fields = input_fields.get(section_def.key, {})
        errors.update(
            validate_choose_fields(
                dict(section_input),
                section_fields,
                field_schema.get(section_def.key, {}),
                exclude_fields=exclude_fields,
            )
        )
    return errors


def convert_sectioned_choose_data_to_config(
    user_input: Mapping[str, Any],
    input_fields: InputFieldGroups,
    sections: Sequence[SectionDefinition],
    *,
    exclude_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Convert sectioned choose data into a sectioned config dict."""
    config: dict[str, Any] = {}
    for section_def in sections:
        section_input = user_input.get(section_def.key, {})
        if not isinstance(section_input, Mapping):
            config[section_def.key] = {}
            continue
        section_fields = input_fields.get(section_def.key, {})
        section_config: dict[str, Any] = {
            key: value
            for key, value in section_input.items()
            if key not in section_fields and key not in exclude_fields
        }
        section_config.update(
            convert_choose_data_to_config(dict(section_input), section_fields, exclude_keys=exclude_fields)
        )
        config[section_def.key] = section_config
    return config


def get_choose_default(
    field_info: InputFieldInfo[Any],
    current_data: Mapping[str, Any] | None = None,
) -> Any:
    """Get the default value for a choose selector field.

    Since ChooseSelector always selects the first choice (which we order
    based on get_preferred_choice), we only need to return the raw value
    for the nested selector - not a {"choice": ..., "value": ...} object.

    Args:
        field_info: Input field metadata.
        current_data: Current configuration data (for reconfigure).

    Returns:
        The value for the nested selector (entity list or constant value),
        or None if no default should be set.

    """
    field_name = field_info.field_name

    # Check current stored data first (for reconfigure)
    current_value = _get_nested_value(current_data, field_name) if current_data is not None else None

    if is_entity_value(current_value):
        return current_value["value"]
    if is_constant_value(current_value):
        return current_value["value"]
    if is_none_value(current_value):
        return None

    # No current data - check defaults
    if field_info.defaults is not None:
        if field_info.defaults.mode == "value" and field_info.defaults.value is not None:
            return field_info.defaults.value
        if field_info.defaults.mode == "entity":
            # Entity mode default - leave empty for user to select
            return []

    # No default
    return None


def convert_choose_data_to_config(
    user_input: dict[str, Any],
    input_fields: Mapping[str, InputFieldInfo[Any]],
    exclude_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Convert choose selector user input to final config format.

    After preprocessing, the user input contains:
    - Entity selection: list of entity IDs (e.g., ["sensor.x"])
    - Constant: scalar value (e.g., 10.0 or True)
    - Disabled/None choice: None

    Args:
        user_input: User input from the form (after preprocessing).
        input_fields: Mapping of input field metadata keyed by field name.
        exclude_keys: Keys to exclude from processing (e.g., name, connection).

    Returns:
        Config dict with discriminated schema values:
        - Entity fields: stored as {"type": "entity", "value": list[str]}
        - Constant fields: stored as {"type": "constant", "value": scalar}
        - Disabled fields: stored as {"type": "none"}

    """
    config: dict[str, Any] = {}
    field_names = set(input_fields)

    for field_name, value in user_input.items():
        if field_name in exclude_keys:
            continue
        if field_name not in field_names:
            continue

        # Disabled/none choice
        if value is None:
            config[field_name] = as_none_value()
            continue

        # Entity selection: list of entity IDs
        if isinstance(value, list):
            if not value:
                config[field_name] = as_none_value()
                continue
            config[field_name] = as_entity_value(normalize_entity_ids(value))
            continue

        # Single entity ID
        if isinstance(value, str):
            if not value:
                config[field_name] = as_none_value()
                continue
            config[field_name] = as_entity_value([value])
            continue

        # Handle numeric or boolean constants
        if isinstance(value, bool):
            config[field_name] = as_constant_value(value)
            continue
        if isinstance(value, Real):
            config[field_name] = as_constant_value(float(value))

    return config


def preprocess_choose_selector_input(
    user_input: dict[str, Any] | None,
    input_fields: Mapping[str, InputFieldInfo[Any]],
) -> dict[str, Any] | None:
    """Preprocess user input to normalize ChooseSelector data.

    Handles the case where the frontend sends raw dict format like:
    {"active_choice": "none", "constant": 100}

    This can occur due to a Home Assistant frontend bug where the previous
    choice's value is included when submitting a different choice.

    Converts to expected format:
    - "none" choice -> None (field will be omitted from config)
    - "entity" choice -> extract entity list
    - "constant" choice -> extract constant value

    Also converts empty strings "" to None for consistency, since HA's
    ConstantSelector returns "" but we use None internally.

    Args:
        user_input: User input from the form submission.
        input_fields: Mapping of input field metadata keyed by field name.

    Returns:
        Normalized user input dict, or None if input was None.

    """
    if user_input is None:
        return None

    result = dict(user_input)
    field_names = set(input_fields)

    for field_name in field_names:
        value = result.get(field_name)

        # Handle raw dict format from frontend bug
        if isinstance(value, dict) and "active_choice" in value:
            choice = value.get("active_choice")
            if choice == CHOICE_NONE:
                result[field_name] = None
            elif choice == CHOICE_ENTITY:
                result[field_name] = value.get(CHOICE_ENTITY, [])
            elif choice == CHOICE_CONSTANT:
                result[field_name] = value.get(CHOICE_CONSTANT)
        # Handle discriminated schema values
        elif is_schema_value(value):
            if is_entity_value(value) or is_constant_value(value):
                result[field_name] = value["value"]
            else:
                result[field_name] = None
        # Convert empty string (from ConstantSelector) to None
        elif value == "":
            result[field_name] = None

    return result


def is_valid_choose_value(value: Any) -> bool:
    """Check if a choose selector value is valid (has a selection).

    After schema validation, ChooseSelector returns the inner value directly
    (list for entities, scalar for constants), not the full dict structure.

    Args:
        value: The value to check.

    Returns:
        True if the value represents a valid selection, False otherwise.

    """
    if value is None:
        return False
    # Entity selection: list of entity IDs
    if isinstance(value, list):
        return bool(value)
    # Constant value: number or boolean
    if isinstance(value, (int, float, bool)):
        return True
    # String value (single entity or other)
    if isinstance(value, str):
        return bool(value)
    return False


def validate_choose_fields(
    user_input: dict[str, Any],
    input_fields: Mapping[str, InputFieldInfo[Any]],
    field_schema: Mapping[str, FieldSchemaInfo],
    *,
    exclude_fields: Collection[str] = (),
) -> dict[str, str]:
    """Validate that required choose fields have valid selections.

    Args:
        user_input: User input dictionary from the form.
        input_fields: Mapping of InputFieldInfo defining the fields.
        field_schema: Mapping of field names to schema metadata.
        exclude_fields: Field names to skip validation for.

    Returns:
        Dictionary of field_name -> error_key for invalid fields.

    """
    errors: dict[str, str] = {}

    for field_name, field_info in input_fields.items():
        if field_name in exclude_fields:
            continue
        schema_info = field_schema.get(field_name)
        if schema_info is None:
            msg = f"Missing schema metadata for field '{field_name}'"
            raise RuntimeError(msg)
        is_optional = schema_info.is_optional and not field_info.force_required

        if is_optional:
            continue

        value = user_input.get(field_name)
        if not is_valid_choose_value(value):
            errors[field_name] = "required"

    return errors


__all__ = [
    "CHOICE_CONSTANT",
    "CHOICE_ENTITY",
    "CHOICE_NONE",
    "NormalizingChooseSelector",
    "SectionDefinition",
    "boolean_selector_from_field",
    "build_choose_field_entries",
    "build_choose_schema_entry",
    "build_choose_selector",
    "build_entity_selector",
    "build_section_schema",
    "convert_choose_data_to_config",
    "convert_sectioned_choose_data_to_config",
    "flatten_section_input",
    "get_choose_default",
    "get_haeo_input_entity_ids",
    "get_preferred_choice",
    "is_valid_choose_value",
    "nest_section_defaults",
    "number_selector_from_field",
    "preprocess_choose_selector_input",
    "preprocess_sectioned_choose_input",
    "resolve_haeo_input_entity_id",
    "validate_choose_fields",
    "validate_sectioned_choose_fields",
]
