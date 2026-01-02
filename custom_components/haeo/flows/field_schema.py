"""Shared utilities for building two-step element config flows.

This module provides utilities for the two-step config flow pattern:
1. Step 1 (user): Select name, connections, and input mode for each field
2. Step 2 (values): Enter values based on selected modes (constant or entity link)

Input modes:
- CONSTANT: User enters a constant value via NumberSelector
- ENTITY_LINK: User selects entities via EntitySelector
- NONE: Field is disabled (only for optional fields with defaults)
"""

from enum import StrEnum
from typing import Any, Final, Protocol

from homeassistant.components.number import NumberEntityDescription
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.elements.input_fields import GroupedInputFields, InputFieldInfo

# Type alias for field groups: tuple of (group_key, tuple of field names)
type FieldGroup = tuple[str, tuple[str, ...]]


class InputMode(StrEnum):
    """Input mode for configurable fields."""

    CONSTANT = "constant"
    ENTITY_LINK = "entity_link"
    NONE = "none"


class ConfigSchemaType(Protocol):
    """Protocol for TypedDict classes used as config schemas.

    This protocol captures the __optional_keys__ attribute that TypedDict
    classes provide, allowing functions to inspect which fields are optional.
    """

    __optional_keys__: frozenset[str]


# Mode suffix appended to field names for mode selectors
MODE_SUFFIX: Final = "_mode"


def build_mode_selector(*, has_default: bool) -> SelectSelector:  # type: ignore[type-arg]
    """Build a mode selector for a configurable field.

    Args:
        has_default: If True, include NONE option (field can be disabled).
                    Required fields should pass False to only show CONSTANT and ENTITY_LINK.

    Returns:
        SelectSelector with appropriate mode options.

    """
    options: list[SelectOptionDict] = [
        SelectOptionDict(value=InputMode.CONSTANT, label=InputMode.CONSTANT),
        SelectOptionDict(value=InputMode.ENTITY_LINK, label=InputMode.ENTITY_LINK),
    ]
    if has_default:
        options.append(SelectOptionDict(value=InputMode.NONE, label=InputMode.NONE))

    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="input_mode",
        )
    )


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


def entity_selector_from_field(
    field_info: InputFieldInfo[Any],
    *,
    exclude_entities: list[str] | None = None,
) -> EntitySelector:  # type: ignore[type-arg]
    """Build an EntitySelector from InputFieldInfo.

    Uses device_class from entity description for filtering when available.

    Args:
        field_info: Input field metadata.
        exclude_entities: Entity IDs to exclude from selection.

    Returns:
        EntitySelector configured for sensor/input_number domains.

    """
    desc = field_info.entity_description

    # Build config kwargs, omitting device_class if not available
    config_kwargs: dict[str, Any] = {
        "domain": ["sensor", "input_number"],
        "multiple": True,
        "exclude_entities": exclude_entities or [],
    }

    # Add device_class filter if available
    if hasattr(desc, "device_class") and desc.device_class is not None:
        config_kwargs["device_class"] = [str(desc.device_class)]

    return EntitySelector(EntitySelectorConfig(**config_kwargs))


def infer_mode_from_value(value: Any) -> InputMode:
    """Infer input mode from a stored config value.

    Used during reconfigure to determine which mode was selected.

    Args:
        value: The stored configuration value.

    Returns:
        InputMode based on value type:
        - list[str] with items → ENTITY_LINK
        - float/int/bool → CONSTANT (note: bool is subclass of int in Python)
        - None or empty list or missing → NONE

    """
    if value is None:
        return InputMode.NONE

    if isinstance(value, list):
        # Non-empty list of entity IDs
        if value and all(isinstance(v, str) for v in value):
            return InputMode.ENTITY_LINK
        # Empty list means disabled
        return InputMode.NONE

    # Scalar value (float, int, bool) means constant
    if isinstance(value, (float, int, bool)):
        return InputMode.CONSTANT

    return InputMode.NONE


def build_mode_schema_entry(
    field_name: str,
    _field_info: InputFieldInfo[Any],
    *,
    config_schema: ConfigSchemaType,
) -> tuple[vol.Marker, Any]:
    """Build a schema entry for mode selection.

    Args:
        field_name: The configuration field name.
        _field_info: Input field metadata (unused but kept for API consistency).
        config_schema: The TypedDict class defining the element's configuration.

    Returns:
        Tuple of (vol.Required marker, SelectSelector).
        For optional fields, defaults to NONE.
        For required fields, no default (user must choose CONSTANT or ENTITY_LINK).

    """
    mode_key = f"{field_name}{MODE_SUFFIX}"
    is_optional = field_name in config_schema.__optional_keys__

    selector = build_mode_selector(has_default=is_optional)

    # Always required, but optional fields get a default of NONE
    if is_optional:
        return vol.Required(mode_key, default=InputMode.NONE), selector
    return vol.Required(mode_key), selector


def build_value_schema_entry(
    field_name: str,
    field_info: InputFieldInfo[Any],
    mode: InputMode,
    *,
    exclude_entities: list[str] | None = None,
) -> tuple[vol.Marker, Any] | None:
    """Build a schema entry for value input based on mode.

    Args:
        field_name: The configuration field name.
        field_info: Input field metadata.
        mode: Selected input mode.
        exclude_entities: Entity IDs to exclude from entity selector.

    Returns:
        Tuple of (vol.Required/Optional marker, Selector) or None if mode is NONE.

    """
    if mode == InputMode.NONE:
        return None

    has_default = field_info.default is not None

    if mode == InputMode.CONSTANT:
        # Build appropriate selector based on entity description type
        # Note: isinstance doesn't work due to Home Assistant's frozen_dataclass_compat wrapper
        if type(field_info.entity_description).__name__ == "SwitchEntityDescription":
            selector = boolean_selector_from_field()
        else:
            selector = number_selector_from_field(field_info)  # type: ignore[arg-type]

        # Optional if has default, required otherwise
        if has_default:
            return vol.Optional(field_name), selector
        return vol.Required(field_name), selector

    if mode == InputMode.ENTITY_LINK:
        entity_selector = entity_selector_from_field(field_info, exclude_entities=exclude_entities)
        # Entity links require at least one entity
        validated_selector = vol.All(
            entity_selector,
            vol.Length(min=1, msg="At least one entity is required"),
        )

        if has_default:
            return vol.Optional(field_name), validated_selector
        return vol.Required(field_name), validated_selector

    return None


def get_mode_defaults(
    input_fields: GroupedInputFields,
    config_schema: ConfigSchemaType,
    current_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get default mode selections for all fields.

    Args:
        input_fields: Grouped input fields dict mapping section keys to field dicts.
        config_schema: The TypedDict class defining the element's configuration.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Nested dict mapping section keys to mode field defaults.

    """
    result: dict[str, Any] = {}

    for group_key, fields_dict in input_fields.items():
        section_defaults: dict[str, str] = {}

        for field_name in fields_dict:
            mode_key = f"{field_name}{MODE_SUFFIX}"

            if current_data is not None:
                # Infer mode from stored value
                value = current_data.get(field_name)
                section_defaults[mode_key] = infer_mode_from_value(value)
            elif field_name in config_schema.__optional_keys__:
                # Default to NONE for optional fields
                section_defaults[mode_key] = InputMode.NONE
            else:
                # Required fields default to CONSTANT
                section_defaults[mode_key] = InputMode.CONSTANT

        if section_defaults:
            result[group_key] = section_defaults

    return result


def get_value_defaults(
    input_fields: GroupedInputFields,
    mode_selections: dict[str, str],
    current_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get default values for the values step based on mode selections.

    Args:
        input_fields: Grouped input fields dict mapping section keys to field dicts.
        mode_selections: Mode selections from step 1.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Nested dict mapping section keys to value defaults.

    """
    result: dict[str, Any] = {}

    for group_key, fields_dict in input_fields.items():
        section_defaults: dict[str, Any] = {}

        for field_name, field_info in fields_dict.items():
            mode_key = f"{field_name}{MODE_SUFFIX}"
            mode = InputMode(mode_selections.get(mode_key, InputMode.NONE))

            if mode == InputMode.NONE:
                continue

            if current_data is not None and field_name in current_data:
                current_value = current_data[field_name]
                current_mode = infer_mode_from_value(current_value)

                # Only use current value if mode matches
                if current_mode == mode:
                    section_defaults[field_name] = current_value
                elif mode == InputMode.CONSTANT and field_info.default is not None:
                    # Switching to constant mode, use default
                    section_defaults[field_name] = field_info.default
            elif mode == InputMode.CONSTANT and field_info.default is not None:
                # New entry with constant mode, use default
                section_defaults[field_name] = field_info.default

        if section_defaults:
            result[group_key] = section_defaults

    return result


def build_grouped_mode_sections(
    input_fields: GroupedInputFields,
    config_schema: ConfigSchemaType,
) -> dict[vol.Marker, Any]:
    """Build mode schema entries organized by group sections.

    Creates sections for grouping related fields in the config flow UI.
    Each group becomes a collapsible section containing mode selectors.

    Args:
        input_fields: Grouped input fields dict mapping section keys to field dicts.
        config_schema: The TypedDict class defining the element's configuration.

    Returns:
        Dict with section-wrapped schema entries ready to merge into schema.

    """
    schema_dict: dict[vol.Marker, Any] = {}

    for group_key, fields_dict in input_fields.items():
        section_schema: dict[vol.Marker, Any] = {}

        for field_name, field_info in fields_dict.items():
            marker, selector = build_mode_schema_entry(
                field_name, field_info, config_schema=config_schema
            )
            section_schema[marker] = selector

        if section_schema:
            # Wrap in section with collapsed by default
            schema_dict[vol.Required(group_key)] = section(
                vol.Schema(section_schema),
                {"collapsed": True},
            )

    return schema_dict


def flatten_sections(
    user_input: dict[str, Any],
    input_fields: GroupedInputFields,
) -> dict[str, Any]:
    """Flatten section-nested user input into a flat dictionary.

    The section() wrapper causes user input to be nested:
    {"group_key": {"field_mode": "constant", ...}, ...}

    This function flattens it back to:
    {"field_mode": "constant", ...}

    Args:
        user_input: Nested user input from form with sections.
        input_fields: Grouped input fields dict to identify section keys.

    Returns:
        Flattened dictionary with all fields at top level.

    """
    result: dict[str, Any] = {}

    for key, value in user_input.items():
        # Check if this key is a section key (exists in input_fields dict)
        if key in input_fields and isinstance(value, dict):
            # Flatten the section contents
            result.update(value)
        else:
            # Keep top-level fields as-is
            result[key] = value

    return result


def build_grouped_value_sections(
    input_fields: GroupedInputFields,
    mode_selections: dict[str, str],
    exclusion_map: dict[str, list[str]],
) -> dict[vol.Marker, Any]:
    """Build value schema entries organized by group sections.

    Creates sections for grouping related fields in step 2 of config flows.
    Each group becomes a collapsible section containing value inputs.

    Args:
        input_fields: Grouped input fields dict mapping section keys to field dicts.
        mode_selections: Mode selections from step 1.
        exclusion_map: Field name -> list of incompatible entity IDs.

    Returns:
        Dict with section-wrapped schema entries ready to merge into schema.

    """
    schema_dict: dict[vol.Marker, Any] = {}

    for group_key, fields_dict in input_fields.items():
        section_schema: dict[vol.Marker, Any] = {}

        for field_name, field_info in fields_dict.items():
            mode_key = f"{field_name}{MODE_SUFFIX}"
            mode_str = mode_selections.get(mode_key, InputMode.NONE)
            mode = InputMode(mode_str) if mode_str else InputMode.NONE

            exclude_entities = exclusion_map.get(field_name, [])
            entry = build_value_schema_entry(field_name, field_info, mode, exclude_entities=exclude_entities)

            if entry is not None:
                marker, selector = entry
                section_schema[marker] = selector

        if section_schema:
            # Wrap in section (collapsed by default)
            schema_dict[vol.Required(group_key)] = section(
                vol.Schema(section_schema),
                {"collapsed": True},
            )

    return schema_dict


__all__ = [
    "MODE_SUFFIX",
    "InputMode",
    "boolean_selector_from_field",
    "build_grouped_mode_sections",
    "build_grouped_value_sections",
    "build_mode_schema_entry",
    "build_mode_selector",
    "build_value_schema_entry",
    "entity_selector_from_field",
    "flatten_sections",
    "get_mode_defaults",
    "get_value_defaults",
    "infer_mode_from_value",
    "number_selector_from_field",
]
