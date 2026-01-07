"""Shared utilities for building two-step element config flows.

This module provides utilities for two config flow patterns:

1. Mode-based pattern (InputMode): Used by battery, load, solar, inverter, etc.
   - Step 1: Select name, connections, and input mode for each field
   - Step 2: Enter values based on selected modes (constant or entity link)
   - Input modes: CONSTANT, ENTITY_LINK, NONE

2. Entity-first pattern (configurable entity): Used by grid
   - Step 1: Select name, connections, and entities (with HAEO Configurable option)
   - Step 2: Enter configurable values for fields where HAEO Configurable was selected
"""

from enum import StrEnum
from typing import Any, Final, Protocol

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import async_get_hass
from homeassistant.helpers import entity_registry as er
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

from custom_components.haeo.const import CONFIGURABLE_ENTITY_UNIQUE_ID, DOMAIN
from custom_components.haeo.elements.input_fields import InputFieldInfo

# =============================================================================
# Mode-based pattern (InputMode) - used by battery, load, solar, inverter, etc.
# =============================================================================


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
    field_info: InputFieldInfo[Any],
    *,
    config_schema: ConfigSchemaType,
) -> tuple[vol.Marker, Any]:
    """Build a schema entry for mode selection.

    Args:
        field_info: Input field metadata.
        config_schema: The TypedDict class defining the element's configuration.

    Returns:
        Tuple of (vol.Required marker, SelectSelector).
        For optional fields, defaults to NONE.
        For required fields, no default (user must choose CONSTANT or ENTITY_LINK).

    """
    mode_key = f"{field_info.field_name}{MODE_SUFFIX}"
    is_optional = field_info.field_name in config_schema.__optional_keys__

    selector = build_mode_selector(has_default=is_optional)

    # Always required, but optional fields get a default of NONE
    if is_optional:
        return vol.Required(mode_key, default=InputMode.NONE), selector
    return vol.Required(mode_key), selector


def build_value_schema_entry(
    field_info: InputFieldInfo[Any],
    mode: InputMode,
    *,
    exclude_entities: list[str] | None = None,
) -> tuple[vol.Marker, Any] | None:
    """Build a schema entry for value input based on mode.

    Args:
        field_info: Input field metadata.
        mode: Selected input mode.
        exclude_entities: Entity IDs to exclude from entity selector.

    Returns:
        Tuple of (vol.Required/Optional marker, Selector) or None if mode is NONE.

    """
    if mode == InputMode.NONE:
        return None

    field_name = field_info.field_name
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
    input_fields: tuple[InputFieldInfo[Any], ...],
    config_schema: ConfigSchemaType,
    current_data: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Get default mode selections for all fields.

    Args:
        input_fields: Tuple of input field metadata.
        config_schema: The TypedDict class defining the element's configuration.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Dict mapping mode field names to default InputMode values.

    """
    defaults: dict[str, str] = {}

    for field_info in input_fields:
        mode_key = f"{field_info.field_name}{MODE_SUFFIX}"

        if current_data is not None:
            # Infer mode from stored value
            value = current_data.get(field_info.field_name)
            defaults[mode_key] = infer_mode_from_value(value)
        elif field_info.field_name in config_schema.__optional_keys__:
            # Default to NONE for optional fields
            defaults[mode_key] = InputMode.NONE
        else:
            # Required fields default to CONSTANT
            defaults[mode_key] = InputMode.CONSTANT

    return defaults


def get_value_defaults(
    input_fields: tuple[InputFieldInfo[Any], ...],
    mode_selections: dict[str, str],
    current_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get default values for the values step based on mode selections.

    Args:
        input_fields: Tuple of input field metadata.
        mode_selections: Mode selections from step 1.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Dict mapping field names to default values.

    """
    defaults: dict[str, Any] = {}

    for field_info in input_fields:
        mode_key = f"{field_info.field_name}{MODE_SUFFIX}"
        mode = InputMode(mode_selections.get(mode_key, InputMode.NONE))

        if mode == InputMode.NONE:
            continue

        field_name = field_info.field_name

        if current_data is not None and field_name in current_data:
            current_value = current_data[field_name]
            current_mode = infer_mode_from_value(current_value)

            # Only use current value if mode matches
            if current_mode == mode:
                defaults[field_name] = current_value
            elif mode == InputMode.CONSTANT and field_info.default is not None:
                # Switching to constant mode, use default
                defaults[field_name] = field_info.default
        elif mode == InputMode.CONSTANT and field_info.default is not None:
            # New entry with constant mode, use default
            defaults[field_name] = field_info.default

    return defaults


# =============================================================================
# Entity-first pattern (configurable entity) - used by grid
# =============================================================================


def is_configurable_entity(entity_id: str) -> bool:
    """Check if an entity ID is the HAEO Configurable sentinel entity.

    Checks by looking up the entity and comparing its unique_id, since users
    may rename the entity_id.

    Args:
        entity_id: Entity ID to check.

    Returns:
        True if the entity is the HAEO Configurable sentinel entity.

    """
    hass = async_get_hass()
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    return entry is not None and entry.unique_id == CONFIGURABLE_ENTITY_UNIQUE_ID


def get_configurable_entity_id() -> str:
    """Get the current entity_id for the configurable sentinel entity.

    Uses the stable unique_id to find the entity, since users may rename the entity_id.

    Returns:
        The current entity_id.

    Raises:
        RuntimeError: If the entity doesn't exist (should never happen after setup).

    """
    hass = async_get_hass()
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID)
    if entity_id is None:
        msg = "Configurable entity not found - sensor platform should have created it during setup"
        raise RuntimeError(msg)
    return entity_id


def resolve_configurable_entity_id(
    entry_id: str,
    subentry_id: str,
    field_name: str,
) -> str | None:
    """Resolve the HAEO-created entity for a configured field.

    When a user configures a field with haeo.configurable_entity and enters
    a value, HAEO creates an input entity (e.g., number.grid_export_limit).
    This function looks up that resolved entity.

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


def is_haeo_input_entity(entity_id: str) -> bool:
    """Check if an entity is a HAEO-created input entity.

    HAEO input entities (number/switch) have unique_ids in the pattern:
    {entry_id}_{subentry_id}_{field_name}

    Args:
        entity_id: Entity ID to check.

    Returns:
        True if the entity is a HAEO input entity.

    """
    hass = async_get_hass()
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.platform != DOMAIN:
        return False
    # HAEO input entities have unique_ids with the pattern: entry_id_subentry_id_field_name
    # They have at least 2 underscores separating 3 parts (minimum for entry_id_subentry_id_field)
    min_underscores = 2
    return entry.unique_id.count("_") >= min_underscores


def build_entity_selector_with_configurable(
    field_info: InputFieldInfo[Any],  # noqa: ARG001
    *,
    exclude_entities: list[str] | None = None,
) -> EntitySelector:  # type: ignore[type-arg]
    """Build an EntitySelector with compatible entities plus the HAEO Configurable entity.

    Does not filter by device_class because:
    1. Unit-based exclusion already narrows down compatible entities
    2. Device class filtering would exclude the configurable sentinel entity
    3. Many real-world sensors lack proper device_class but have correct units

    The configurable entity is always included via the 'haeo' domain.

    Args:
        field_info: Input field metadata (kept for API consistency, may be used for
            device_class filtering in future).
        exclude_entities: Entity IDs to exclude from selection (already filtered by unit compatibility).

    Returns:
        EntitySelector configured for sensor/input_number/haeo domains.

    """
    # Remove configurable entity from exclude list (it has unit_of_measurement=None
    # which fails unit filtering, but we always want it available)
    filtered_exclude = [entity_id for entity_id in (exclude_entities or []) if not is_configurable_entity(entity_id)]

    # Build config - no device_class filter, rely on unit-based exclusion
    # Include 'number' and 'switch' so HAEO input entities can be re-selected during reconfigure
    # The configurable sentinel is a sensor entity, so it's included via 'sensor' domain
    config_kwargs: dict[str, Any] = {
        "domain": [DOMAIN, "sensor", "input_number", "number", "switch"],
        "multiple": True,
        "exclude_entities": filtered_exclude,
    }

    return EntitySelector(EntitySelectorConfig(**config_kwargs))


def build_entity_schema_entry(
    field_info: InputFieldInfo[Any],
    *,
    config_schema: ConfigSchemaType,
    exclude_entities: list[str] | None = None,
) -> tuple[vol.Marker, Any]:
    """Build a schema entry for entity selection (step 1).

    Args:
        field_info: Input field metadata.
        config_schema: The TypedDict class defining the element's configuration.
        exclude_entities: Entity IDs to exclude from selection.

    Returns:
        Tuple of (vol.Required/Optional marker, EntitySelector).
        Required fields default to the configurable entity.
        Optional fields default to empty list.

    """
    field_name = field_info.field_name
    is_optional = field_name in config_schema.__optional_keys__

    selector = build_entity_selector_with_configurable(
        field_info,
        exclude_entities=exclude_entities,
    )

    # Don't set defaults in schema - EntitySelector doesn't respect them
    # Defaults are applied via add_suggested_values_to_schema() instead
    # This ensures "Select an entity" placeholder shows for all empty fields
    if is_optional:
        return vol.Optional(field_name), selector
    return vol.Required(field_name), selector


def build_configurable_value_schema_entry(
    field_info: InputFieldInfo[Any],
) -> tuple[vol.Marker, Any]:
    """Build a schema entry for configurable value input (step 2).

    Args:
        field_info: Input field metadata.

    Returns:
        Tuple of (vol.Required/Optional marker, Selector) for configurable value input.

    """
    field_name = field_info.field_name
    has_default = field_info.default is not None

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


def build_configurable_value_schema(
    input_fields: tuple[InputFieldInfo[Any], ...],
    entity_selections: dict[str, list[str]],
    current_data: dict[str, Any] | None = None,  # noqa: ARG001
) -> vol.Schema:
    """Build schema for step 2 with configurable value inputs.

    Only includes fields where HAEO Configurable sentinel is in the entity selection.
    When user selects the configurable sentinel, they always want to enter/change a value,
    so the form is always shown regardless of any stored value.

    Note: If user keeps a resolved HAEO entity selected (e.g., number.grid_import_price),
    is_configurable_entity() returns False and the field won't be included, so step 2
    is skipped automatically.

    Args:
        input_fields: Tuple of input field metadata.
        entity_selections: Entity selections from step 1 (field_name -> list of entity IDs).
        current_data: Current configuration data (unused, kept for API compatibility).

    Returns:
        Schema with configurable value inputs for fields with HAEO Configurable selected.

    """
    schema_dict: dict[vol.Marker, Any] = {}

    for field_info in input_fields:
        field_name = field_info.field_name
        selected_entities = entity_selections.get(field_name, [])

        # Skip fields without configurable sentinel selection
        # (resolved HAEO entities like number.grid_import_price return False here)
        if not any(is_configurable_entity(entity_id) for entity_id in selected_entities):
            continue

        # User selected haeo.configurable_entity - always show form for value entry
        marker, selector = build_configurable_value_schema_entry(field_info)
        schema_dict[marker] = selector

    return vol.Schema(schema_dict)


def get_configurable_value_defaults(
    input_fields: tuple[InputFieldInfo[Any], ...],
    entity_selections: dict[str, list[str]],
    current_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get default configurable values for step 2.

    Args:
        input_fields: Tuple of input field metadata.
        entity_selections: Entity selections from step 1.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Dict mapping field names to default configurable values.
        Only includes fields where HAEO Configurable is selected.

    """
    defaults: dict[str, Any] = {}

    for field_info in input_fields:
        field_name = field_info.field_name
        selected_entities = entity_selections.get(field_name, [])

        # Only provide defaults for fields with configurable entity
        if not any(is_configurable_entity(entity_id) for entity_id in selected_entities):
            continue

        if current_data is not None and field_name in current_data:
            current_value = current_data[field_name]
            # If current value is a scalar (float/int/bool), use it
            if isinstance(current_value, (float, int, bool)):
                defaults[field_name] = current_value
            elif field_info.default is not None:
                defaults[field_name] = field_info.default
        elif field_info.default is not None:
            defaults[field_name] = field_info.default

    return defaults


def has_configurable_selection(entity_selection: list[str]) -> bool:
    """Check if the HAEO Configurable entity is in the entity selection.

    Args:
        entity_selection: List of selected entity IDs.

    Returns:
        True if the configurable entity is in the selection.

    """
    return any(is_configurable_entity(entity_id) for entity_id in entity_selection)


def extract_entity_selections(
    step1_data: dict[str, Any],
    exclude_keys: tuple[str, ...] = (),
) -> dict[str, list[str]]:
    """Extract entity selections (list fields) from step 1 data.

    Args:
        step1_data: Data from step 1 of the flow.
        exclude_keys: Keys to exclude (e.g., name, connection fields).

    Returns:
        Dict mapping field names to entity ID lists.

    """
    return {k: v for k, v in step1_data.items() if k not in exclude_keys and isinstance(v, list)}


def extract_non_entity_fields(
    step1_data: dict[str, Any],
    exclude_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Extract non-entity fields (non-list values) from step 1 data.

    Args:
        step1_data: Data from step 1 of the flow.
        exclude_keys: Keys to exclude (e.g., name, connection fields).

    Returns:
        Dict mapping field names to their values.

    """
    return {k: v for k, v in step1_data.items() if k not in exclude_keys and not isinstance(v, list)}


def convert_entity_selections_to_config(
    entity_selections: dict[str, list[str]],
    configurable_values: dict[str, Any],
    input_fields: tuple[InputFieldInfo[Any], ...] | None = None,
    current_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert entity selections and configurable values to final config format.

    Args:
        entity_selections: Entity selections from step 1.
        configurable_values: Configurable values from step 2.
        input_fields: Optional tuple of input field metadata. If provided, applies
            defaults for optional fields with no selection.
        current_data: Current stored config (for reconfigure). Used to preserve
            scalar values when HAEO input entities are kept selected.

    Returns:
        Config dict with:
        - Fields with configurable entity: converted to float (from configurable_values)
        - Fields with HAEO input entity kept: preserved scalar value from current_data
        - Fields with real external entities: kept as list[str]
        - Fields with empty selection but default: set to default value
        - Fields with empty selection and no default: omitted

    """
    config: dict[str, Any] = {}

    # Build a map of field defaults
    field_defaults: dict[str, Any] = {}
    if input_fields:
        for field_info in input_fields:
            if field_info.default is not None:
                field_defaults[field_info.field_name] = field_info.default

    for field_name, entities in entity_selections.items():
        if not entities:
            # Empty selection - apply default if available
            if field_name in field_defaults:
                config[field_name] = field_defaults[field_name]
            # Otherwise omit from config (truly optional with no default)
            continue

        if any(is_configurable_entity(entity_id) for entity_id in entities):
            # Configurable sentinel selected - get value from configurable_values
            if field_name in configurable_values:
                config[field_name] = configurable_values[field_name]
            # If configurable entity is selected but no value provided, skip (validation should catch this)
        elif any(is_haeo_input_entity(entity_id) for entity_id in entities):
            # HAEO input entity kept selected - preserve original scalar value
            if current_data is not None and field_name in current_data:
                current_value = current_data[field_name]
                if isinstance(current_value, (float, int, bool)):
                    config[field_name] = current_value
                else:
                    # Unexpected: HAEO input entity but no scalar in current_data
                    config[field_name] = entities
            else:
                # No current_data - shouldn't happen but fall back to entity list
                config[field_name] = entities
        else:
            # Real external entities - keep as list
            config[field_name] = entities

    return config


__all__ = [
    "MODE_SUFFIX",
    "InputMode",
    "boolean_selector_from_field",
    "build_configurable_value_schema",
    "build_configurable_value_schema_entry",
    "build_entity_schema_entry",
    "build_entity_selector_with_configurable",
    "build_mode_schema_entry",
    "build_mode_selector",
    "build_value_schema_entry",
    "convert_entity_selections_to_config",
    "entity_selector_from_field",
    "extract_entity_selections",
    "extract_non_entity_fields",
    "get_configurable_entity_id",
    "get_configurable_value_defaults",
    "get_mode_defaults",
    "get_value_defaults",
    "has_configurable_selection",
    "infer_mode_from_value",
    "is_configurable_entity",
    "is_haeo_input_entity",
    "number_selector_from_field",
    "resolve_configurable_entity_id",
]
