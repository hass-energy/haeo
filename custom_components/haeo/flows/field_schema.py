"""Shared utilities for building entity-first two-step element config flows.

This module provides utilities for the entity-first config flow pattern:

- Step 1: Select name, connections, and entities (with HAEO Configurable option)
- Step 2: Enter configurable values for fields where HAEO Configurable was selected
"""

from typing import Any, Protocol

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import async_get_hass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
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

from custom_components.haeo.const import CONFIGURABLE_ENTITY_UNIQUE_ID, DOMAIN
from custom_components.haeo.elements.input_fields import InputFieldInfo


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

    HAEO input entities are number/switch entities created by the haeo platform.

    Args:
        entity_id: Entity ID to check.

    Returns:
        True if the entity is a HAEO input entity.

    """
    hass = async_get_hass()
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None:
        return False
    return entry.platform == DOMAIN and entry.domain in ("number", "switch")


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


def build_entity_selector_with_configurable(
    field_info: InputFieldInfo[Any],  # noqa: ARG001
    *,
    include_entities: list[str] | None = None,
) -> EntitySelector:  # type: ignore[type-arg]
    """Build an EntitySelector with compatible entities plus the HAEO Configurable entity.

    Uses an inclusion list for better performance - only compatible entities are
    included rather than excluding all incompatible ones.

    Args:
        field_info: Input field metadata (kept for API consistency, may be used for
            device_class filtering in future).
        include_entities: Entity IDs to include (compatible entities from unit filtering).

    Returns:
        EntitySelector configured with include_entities list.

    """
    # Start with compatible entities from unit filtering
    entities_to_include = list(include_entities or [])

    # Always include configurable sentinel entity
    entities_to_include.append(get_configurable_entity_id())

    # Include all HAEO input entities so they can be re-selected during reconfigure
    # These entities may not pass unit filtering (e.g., price fields lack currency units)
    # but should always be available for their original fields
    entities_to_include.extend(get_haeo_input_entity_ids())

    # Use include_entities for better performance with large HA installations
    # Domain filter ensures we only show entities from relevant domains even if
    # entities from other domains happen to have matching units
    config_kwargs: dict[str, Any] = {
        "domain": [DOMAIN, "sensor", "input_number", "number", "switch"],
        "multiple": True,
        "include_entities": entities_to_include,
    }

    return EntitySelector(EntitySelectorConfig(**config_kwargs))


def build_entity_schema_entry(
    field_info: InputFieldInfo[Any],
    *,
    config_schema: ConfigSchemaType,
    include_entities: list[str] | None = None,
) -> tuple[vol.Marker, Any]:
    """Build a schema entry for entity selection (step 1).

    Args:
        field_info: Input field metadata.
        config_schema: The TypedDict class defining the element's configuration.
        include_entities: Entity IDs to include (compatible entities from unit filtering).

    Returns:
        Tuple of (vol.Required/Optional marker, EntitySelector).
        Required fields default to the configurable entity.
        Optional fields default to empty list.

    """
    field_name = field_info.field_name
    is_optional = field_name in config_schema.__optional_keys__

    selector = build_entity_selector_with_configurable(
        field_info,
        include_entities=include_entities,
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

    Step 2 fields are always Required. The defaults.value is only used
    for pre-filling the form, not as a fallback.

    Args:
        field_info: Input field metadata.

    Returns:
        Tuple of (vol.Required marker, Selector) for configurable value input.

    """
    field_name = field_info.field_name

    # Build appropriate selector based on entity description type
    # Note: isinstance doesn't work due to Home Assistant's frozen_dataclass_compat wrapper
    if type(field_info.entity_description).__name__ == "SwitchEntityDescription":
        selector = boolean_selector_from_field()
    else:
        selector = number_selector_from_field(field_info)  # type: ignore[arg-type]

    # Always required - user must provide a value when configurable is selected
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

    These values are used to pre-fill the form, not as fallbacks.
    Step 2 fields are always Required.

    Args:
        input_fields: Tuple of input field metadata.
        entity_selections: Entity selections from step 1.
        current_data: Current configuration data (for reconfigure).

    Returns:
        Dict mapping field names to suggested values for pre-filling.
        Only includes fields where HAEO Configurable is selected.

    """
    suggested: dict[str, Any] = {}

    for field_info in input_fields:
        field_name = field_info.field_name
        selected_entities = entity_selections.get(field_name, [])

        # Only provide suggestions for fields with configurable entity
        if not any(is_configurable_entity(entity_id) for entity_id in selected_entities):
            continue

        # Priority: current stored value > defaults.value
        if current_data is not None and field_name in current_data:
            current_value = current_data[field_name]
            # If current value is a scalar (float/int/bool), use it
            if isinstance(current_value, (float, int, bool)):
                suggested[field_name] = current_value
                continue

        # Use defaults.value if available
        if field_info.defaults is not None and field_info.defaults.value is not None:
            suggested[field_name] = field_info.defaults.value

    return suggested


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
    input_fields: tuple[InputFieldInfo[Any], ...] | None = None,  # noqa: ARG001
    current_data: dict[str, Any] | None = None,
    *,
    entry_id: str | None = None,
    subentry_id: str | None = None,
) -> dict[str, Any]:
    """Convert entity selections and configurable values to final config format.

    Args:
        entity_selections: Entity selections from step 1.
        configurable_values: Configurable values from step 2.
        input_fields: Unused, kept for API compatibility.
        current_data: Current stored config (for reconfigure). Used to preserve
            scalar values when self-referential entities are selected.
        entry_id: Config entry ID (for detecting self-referential selections).
        subentry_id: Subentry ID (for detecting self-referential selections).

    Returns:
        Config dict with:
        - Fields with configurable entity: converted to float (from configurable_values)
        - Fields with self-referential entity: preserved scalar value from current_data
        - Fields with single entity: stored as str (single entity ID)
        - Fields with multiple entities: stored as list[str] (for chaining)
        - Fields with empty selection: omitted (no default fallback)

    """
    config: dict[str, Any] = {}

    for field_name, entities in entity_selections.items():
        if not entities:
            # Empty selection - always omit from config
            # Requiredness is enforced by schema validation, not here
            continue

        if any(is_configurable_entity(entity_id) for entity_id in entities):
            # Configurable sentinel selected - get value from configurable_values
            if field_name in configurable_values:
                config[field_name] = configurable_values[field_name]
            # If configurable entity is selected but no value provided, skip (validation should catch this)
        elif entry_id and subentry_id and _is_self_referential(entities, entry_id, subentry_id, field_name):
            # Self-referential selection (this field's own entity is selected)
            # Preserve the original scalar value from current_data
            if current_data is None:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="self_referential_no_current_data",
                    translation_placeholders={"field": field_name},
                )
            if field_name not in current_data:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="self_referential_field_missing",
                    translation_placeholders={"field": field_name},
                )
            current_value = current_data[field_name]
            if not isinstance(current_value, (float, int, bool)):
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="self_referential_invalid_value",
                    translation_placeholders={
                        "field": field_name,
                        "value_type": type(current_value).__name__,
                    },
                )
            config[field_name] = current_value
        else:
            # Real external entities (including other HAEO entities) - store as entity reference
            config[field_name] = _normalize_entity_selection(entities)

    return config


def _is_self_referential(
    entities: list[str],
    entry_id: str,
    subentry_id: str,
    field_name: str,
) -> bool:
    """Check if any selected entity is the self-referential entity for this field.

    Returns True if the entity list contains the entity that would be created
    from this exact entry_id/subentry_id/field_name combination.
    """
    self_entity_id = resolve_configurable_entity_id(entry_id, subentry_id, field_name)
    if self_entity_id is None:
        return False
    return self_entity_id in entities


def _normalize_entity_selection(entities: list[str]) -> str | list[str]:
    """Normalize entity selection to str (single) or list[str] (multiple).

    Single entity selections are stored as strings for v0.1 format compatibility.
    Multiple entity selections are stored as lists for chaining support.
    """
    if len(entities) == 1:
        return entities[0]
    return entities


__all__ = [
    "ConfigSchemaType",
    "boolean_selector_from_field",
    "build_configurable_value_schema",
    "build_configurable_value_schema_entry",
    "build_entity_schema_entry",
    "build_entity_selector_with_configurable",
    "convert_entity_selections_to_config",
    "extract_entity_selections",
    "extract_non_entity_fields",
    "get_configurable_entity_id",
    "get_configurable_value_defaults",
    "get_haeo_input_entity_ids",
    "has_configurable_selection",
    "is_configurable_entity",
    "is_haeo_input_entity",
    "number_selector_from_field",
    "resolve_configurable_entity_id",
]
