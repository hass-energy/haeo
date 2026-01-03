"""Shared utilities for building two-step element config flows.

This module provides utilities for the entity-first config flow pattern:
1. Step 1 (user): Select name, connections, and entities for each field (with HAEO Configurable option)
2. Step 2 (values): Enter constant values for fields where HAEO Configurable was selected
"""

from typing import Any, Protocol

from homeassistant.components.number import NumberEntityDescription
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.const import DOMAIN, HAEO_CONFIGURABLE_ENTITY_ID
from custom_components.haeo.elements.input_fields import InputFieldInfo


def is_constant_entity(entity_id: str) -> bool:
    """Check if an entity ID is the constant sentinel entity.

    Args:
        entity_id: Entity ID to check.

    Returns:
        True if the entity is a constant sentinel entity.

    """
    return entity_id == HAEO_CONFIGURABLE_ENTITY_ID


class ConfigSchemaType(Protocol):
    """Protocol for TypedDict classes used as config schemas.

    This protocol captures the __optional_keys__ attribute that TypedDict
    classes provide, allowing functions to inspect which fields are optional.
    """

    __optional_keys__: frozenset[str]


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


def build_entity_selector_with_constant(
    field_info: InputFieldInfo[Any],  # noqa: ARG001
    *,
    exclude_entities: list[str] | None = None,
) -> EntitySelector:  # type: ignore[type-arg]
    """Build an EntitySelector with compatible entities plus the constant entity.

    Does not filter by device_class because:
    1. Unit-based exclusion already narrows down compatible entities
    2. Device class filtering would exclude the haeo.configurable_entity entity
    3. Many real-world sensors lack proper device_class but have correct units

    The configurable entity (haeo.configurable_entity) is always included via the 'haeo' domain.

    Args:
        field_info: Input field metadata (kept for API consistency, may be used for
            device_class filtering in future).
        exclude_entities: Entity IDs to exclude from selection (already filtered by unit compatibility).

    Returns:
        EntitySelector configured for sensor/input_number/haeo domains.

    """
    # Remove constant entity from exclude list (it has unit_of_measurement=None
    # which fails unit filtering, but we always want it available)
    filtered_exclude = [entity_id for entity_id in (exclude_entities or []) if not is_constant_entity(entity_id)]

    # Build config - no device_class filter, rely on unit-based exclusion
    # Include 'haeo' domain so haeo.configurable_entity always appears
    # Include 'number' and 'switch' so HAEO input entities can be re-selected during reconfigure
    config_kwargs: dict[str, Any] = {
        "domain": ["sensor", "input_number", "number", "switch", DOMAIN],
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
        Required fields default to the appropriate constant entity for their device_class.
        Optional fields default to empty list.

    """
    field_name = field_info.field_name
    is_optional = field_name in config_schema.__optional_keys__

    selector = build_entity_selector_with_constant(
        field_info,
        exclude_entities=exclude_entities,
    )

    # Don't set default in vol.Required - EntitySelector doesn't respect it
    # Defaults are applied via add_suggested_values_to_schema() instead
    if is_optional:
        return vol.Optional(field_name, default=[]), selector
    return vol.Required(field_name), selector


def build_constant_value_schema_entry(
    field_info: InputFieldInfo[Any],
) -> tuple[vol.Marker, Any]:
    """Build a schema entry for constant value input (step 2).

    Args:
        field_info: Input field metadata.

    Returns:
        Tuple of (vol.Required/Optional marker, Selector) for constant value input.

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


def build_constant_value_schema(
    input_fields: tuple[InputFieldInfo[Any], ...],
    entity_selections: dict[str, list[str]],
    current_data: dict[str, Any] | None = None,
) -> vol.Schema:
    """Build schema for step 2 with constant value inputs.

    Only includes fields where HAEO Configurable is in the entity selection.
    When current_data is provided (for reconfigure), fields that already have
    stored constant values are excluded from the schema.

    Args:
        input_fields: Tuple of input field metadata.
        entity_selections: Entity selections from step 1 (field_name -> list of entity IDs).
        current_data: Current configuration data (for reconfigure). Fields with
            stored constant values will be excluded from the schema.

    Returns:
        Schema with constant value inputs for fields with HAEO Configurable that
        need user input.

    """
    schema_dict: dict[vol.Marker, Any] = {}

    for field_info in input_fields:
        field_name = field_info.field_name
        selected_entities = entity_selections.get(field_name, [])

        # Skip fields without constant selection
        if not any(is_constant_entity(entity_id) for entity_id in selected_entities):
            continue

        # For reconfigure, skip fields that already have stored constant values
        # But include fields where user is switching from entity to constant (current_value is list)
        if current_data is not None:
            current_value = current_data.get(field_name)
            # If current value is a scalar constant, we can reuse it
            if isinstance(current_value, (float, int, bool)):
                continue
            # If current value is a list (entity IDs), user is switching TO constant - need input
            if isinstance(current_value, list):
                pass  # Include in schema
            # If field has a default and no prior value, use the default
            elif field_info.default is not None:
                continue

        marker, selector = build_constant_value_schema_entry(field_info)
        schema_dict[marker] = selector

    return vol.Schema(schema_dict)


def get_entity_selection_defaults(
    input_fields: tuple[InputFieldInfo[Any], ...],
    config_schema: ConfigSchemaType,
    current_data: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Get default entity selections for all fields.

    Args:
        input_fields: Tuple of input field metadata.
        config_schema: TypedDict class to check which fields are optional.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Dict mapping field names to default entity selections.
        Required fields and optional fields with defaults: default to constant entity.
        Optional fields without defaults: default to empty list (nothing selected).
        For reconfigure, infers from stored values.

    """
    defaults: dict[str, list[str]] = {}

    for field_info in input_fields:
        field_name = field_info.field_name

        if current_data is not None and field_name in current_data:
            # Infer from stored value
            value = current_data[field_name]
            if isinstance(value, list) and value:
                # Entity links
                defaults[field_name] = value
            elif isinstance(value, (float, int, bool)):
                # Constant value - use constant entity
                defaults[field_name] = [HAEO_CONFIGURABLE_ENTITY_ID]
            else:
                # Missing or invalid - use appropriate default based on field type
                is_optional = field_name in config_schema.__optional_keys__
                if is_optional and field_info.default is None:
                    defaults[field_name] = []
                else:
                    defaults[field_name] = [HAEO_CONFIGURABLE_ENTITY_ID]
        else:
            # New entry - default based on whether field is optional without a default
            is_optional = field_name in config_schema.__optional_keys__
            if is_optional and field_info.default is None:
                # Optional field with no default: nothing selected
                defaults[field_name] = []
            else:
                # Required field or optional with default: use constant entity
                defaults[field_name] = [HAEO_CONFIGURABLE_ENTITY_ID]

    return defaults


def get_constant_value_defaults(
    input_fields: tuple[InputFieldInfo[Any], ...],
    entity_selections: dict[str, list[str]],
    current_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get default constant values for step 2.

    Args:
        input_fields: Tuple of input field metadata.
        entity_selections: Entity selections from step 1.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Dict mapping field names to default constant values.
        Only includes fields where HAEO Configurable is selected.

    """
    defaults: dict[str, Any] = {}

    for field_info in input_fields:
        field_name = field_info.field_name
        selected_entities = entity_selections.get(field_name, [])

        # Only provide defaults for fields with constant entity
        if not any(is_constant_entity(entity_id) for entity_id in selected_entities):
            continue

        if current_data is not None and field_name in current_data:
            current_value = current_data[field_name]
            # If current value is a constant (float/int/bool), use it
            if isinstance(current_value, (float, int, bool)):
                defaults[field_name] = current_value
            elif field_info.default is not None:
                defaults[field_name] = field_info.default
        elif field_info.default is not None:
            defaults[field_name] = field_info.default

    return defaults


def has_constant_selection(entity_selection: list[str]) -> bool:
    """Check if any constant sentinel entity is in the entity selection.

    Args:
        entity_selection: List of selected entity IDs.

    Returns:
        True if any constant entity is in the selection.

    """
    return any(is_constant_entity(entity_id) for entity_id in entity_selection)


def can_reuse_constant_values(
    input_fields: tuple[InputFieldInfo[Any], ...],
    entity_selections: dict[str, list[str]],
    current_data: dict[str, Any],
) -> bool:
    """Check if all constant fields have valid values in current_data.

    Used during reconfiguration to skip the constant values step when
    all fields with constant entity selections already have stored values.

    If a field was previously configured as an entity (list) and the user
    switches to haeo.configurable_entity, we need to ask for the new value.

    Args:
        input_fields: Tuple of input field metadata.
        entity_selections: Entity selections from step 1 (field_name -> list of entity IDs).
        current_data: Current configuration data from the subentry.

    Returns:
        True if all constant fields have stored constant values or defaults.

    """
    for field_info in input_fields:
        field_name = field_info.field_name
        selected_entities = entity_selections.get(field_name, [])

        # Skip fields without constant selection
        if not has_constant_selection(selected_entities):
            continue

        # Check if current_data has a valid constant value for this field
        current_value = current_data.get(field_name)

        # A stored constant value is a float/int/bool (not a list of entities)
        if isinstance(current_value, (float, int, bool)):
            continue

        # If current_value is a list (entity IDs), user is switching TO haeo.configurable_entity
        # from a previously configured entity - need to ask for the new value
        if isinstance(current_value, list):
            return False

        # Check if field has a default value we can use
        if field_info.default is not None:
            continue

        # No stored value and no default - need user input
        return False

    return True


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
    constant_values: dict[str, Any],
    input_fields: tuple[InputFieldInfo[Any], ...] | None = None,
) -> dict[str, Any]:
    """Convert entity selections and constant values to final config format.

    Args:
        entity_selections: Entity selections from step 1.
        constant_values: Constant values from step 2.
        input_fields: Optional tuple of input field metadata. If provided, applies
            defaults for optional fields with no selection.

    Returns:
        Config dict with:
        - Fields with constant entity: converted to float (from constant_values)
        - Fields with real entities: kept as list[str]
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

        if any(is_constant_entity(entity_id) for entity_id in entities):
            # Constant value - get from constant_values
            if field_name in constant_values:
                config[field_name] = constant_values[field_name]
            # If constant entity is selected but no value provided, skip (validation should catch this)
        else:
            # Real entities - keep as list
            config[field_name] = entities

    return config


__all__ = [
    "boolean_selector_from_field",
    "build_constant_value_schema",
    "build_constant_value_schema_entry",
    "build_entity_schema_entry",
    "build_entity_selector_with_constant",
    "can_reuse_constant_values",
    "convert_entity_selections_to_config",
    "extract_entity_selections",
    "extract_non_entity_fields",
    "get_constant_value_defaults",
    "get_entity_selection_defaults",
    "has_constant_selection",
    "is_constant_entity",
    "number_selector_from_field",
]
