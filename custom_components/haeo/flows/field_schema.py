"""Shared utilities for building element config flows with choose selectors.

This module provides utilities for the unified config flow pattern using
Home Assistant's ChooseSelector, allowing users to pick between "Entity"
(select from compatible sensors) or "Constant" (enter a value directly).
"""

from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import async_get_hass
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
from custom_components.haeo.elements.input_fields import InputFieldInfo

# Choose selector choice keys (used for config flow data and translations)
CHOICE_ENTITY = "entity"
CHOICE_CONSTANT = "constant"
CHOICE_DISABLED = "disabled"


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


def get_preferred_choice(
    field_info: InputFieldInfo[Any],
    current_data: dict[str, Any] | None = None,
    *,
    is_optional: bool = False,
) -> str:
    """Determine which choice should be first in the ChooseSelector.

    The ChooseSelector always selects the first choice, so we order
    choices based on what should be pre-selected.

    Args:
        field_info: Input field metadata.
        current_data: Current configuration data (for reconfigure).
        is_optional: Whether the field is optional (enables "disabled" choice).

    Returns:
        CHOICE_ENTITY, CHOICE_CONSTANT, or CHOICE_DISABLED based on context.

    """
    field_name = field_info.field_name

    # Check current stored data first (for reconfigure)
    if current_data is not None:
        if field_name in current_data:
            current_value = current_data[field_name]
            # String = entity ID, number/bool = constant
            if isinstance(current_value, str):
                return CHOICE_ENTITY
            return CHOICE_CONSTANT
        # Field not in current_data means it was disabled (for optional fields)
        if is_optional:
            return CHOICE_DISABLED

    # For new entries, use field defaults
    if field_info.defaults is not None:
        if field_info.defaults.mode == "value":
            return CHOICE_CONSTANT
        if field_info.defaults.mode == "entity":
            return CHOICE_ENTITY
        # mode is None means default to disabled for optional fields
        if is_optional and field_info.defaults.mode is None:
            return CHOICE_DISABLED

    # For optional fields with no defaults, default to disabled
    if is_optional and field_info.defaults is None:
        return CHOICE_DISABLED

    # Default to entity
    return CHOICE_ENTITY


def build_choose_selector(
    field_info: InputFieldInfo[Any],
    *,
    is_optional: bool = False,
    include_entities: list[str] | None = None,
    multiple: bool = True,
    preferred_choice: str = CHOICE_ENTITY,
) -> Any:
    """Build a ChooseSelector allowing user to pick Entity, Constant, or Disabled.

    Args:
        field_info: Input field metadata.
        is_optional: Whether the field is optional (adds "disabled" choice).
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
    disabled_selector = ConstantSelector(ConstantSelectorConfig(value="", translation_key="disabled_label"))
    disabled_choice = ChooseSelectorChoiceConfig(selector=disabled_selector.serialize()["selector"])

    if is_optional and preferred_choice == CHOICE_DISABLED:
        # Optional field with disabled preferred
        choices = {
            CHOICE_DISABLED: disabled_choice,
            CHOICE_ENTITY: entity_choice,
            CHOICE_CONSTANT: constant_choice,
        }
    elif is_optional and preferred_choice == CHOICE_CONSTANT:
        # Optional field with constant preferred
        choices = {
            CHOICE_CONSTANT: constant_choice,
            CHOICE_ENTITY: entity_choice,
            CHOICE_DISABLED: disabled_choice,
        }
    elif is_optional:
        # Optional field with entity preferred
        choices = {
            CHOICE_ENTITY: entity_choice,
            CHOICE_CONSTANT: constant_choice,
            CHOICE_DISABLED: disabled_choice,
        }
    elif preferred_choice == CHOICE_CONSTANT:
        # Required field with constant preferred
        choices = {
            CHOICE_CONSTANT: constant_choice,
            CHOICE_ENTITY: entity_choice,
        }
    else:
        # Required field with entity preferred (default)
        choices = {
            CHOICE_ENTITY: entity_choice,
            CHOICE_CONSTANT: constant_choice,
        }

    return ChooseSelector(
        ChooseSelectorConfig(
            choices=choices,
            translation_key="input_source",
        )
    )


def build_choose_schema_entry(
    field_info: InputFieldInfo[Any],
    *,
    is_optional: bool,
    include_entities: list[str] | None = None,
    multiple: bool = True,
    preferred_choice: str = CHOICE_ENTITY,
) -> tuple[vol.Marker, Any]:
    """Build a schema entry using ChooseSelector.

    Args:
        field_info: Input field metadata.
        is_optional: Whether the field is optional (adds "disabled" choice).
        include_entities: Entity IDs to include (compatible entities from unit filtering).
        multiple: Whether to allow multiple entity selection.
        preferred_choice: Which choice should appear first (will be pre-selected).

    Returns:
        Tuple of (vol.Required/Optional marker, ChooseSelector).

    """
    field_name = field_info.field_name
    selector = build_choose_selector(
        field_info,
        is_optional=is_optional,
        include_entities=include_entities,
        multiple=multiple,
        preferred_choice=preferred_choice,
    )

    if is_optional:
        return vol.Optional(field_name), selector
    return vol.Required(field_name), selector


def get_choose_default(
    field_info: InputFieldInfo[Any],
    current_data: dict[str, Any] | None = None,
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
    if current_data is not None and field_name in current_data:
        current_value = current_data[field_name]

        if isinstance(current_value, (float, int)) and not isinstance(current_value, bool):
            # Constant numeric value
            return current_value
        if isinstance(current_value, bool):
            # Boolean constant
            return current_value
        if isinstance(current_value, str):
            # Single entity ID - wrap in list for entity selector
            return [current_value]
        if isinstance(current_value, list):
            # Multiple entity IDs
            return current_value

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
    input_fields: tuple[InputFieldInfo[Any], ...],
    exclude_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Convert choose selector user input to final config format.

    After schema validation, the ChooseSelector returns the inner value directly:
    - Entity selection: list of entity IDs (e.g., ["sensor.x"])
    - Constant: scalar value (e.g., 10.0 or True)
    - Disabled: empty string ("")

    Args:
        user_input: User input from the form (after schema validation).
        input_fields: Tuple of input field metadata.
        exclude_keys: Keys to exclude from processing (e.g., name, connection).

    Returns:
        Config dict with:
        - Constant fields: stored as float/bool
        - Entity fields with single entity: stored as str
        - Entity fields with multiple entities: stored as list[str]
        - Empty/None/Disabled fields: omitted

    """
    config: dict[str, Any] = {}
    field_names = {f.field_name for f in input_fields}

    for field_name, value in user_input.items():
        if field_name in exclude_keys:
            continue
        if field_name not in field_names:
            continue

        # Skip None values
        if value is None:
            continue

        # Disabled choice returns empty string - skip
        if value == "":
            continue

        # Entity selection: list of entity IDs
        if isinstance(value, list):
            if not value:
                continue  # Empty list - skip
            config[field_name] = _normalize_entity_selection(value)
        # Constant: scalar value (number, boolean, or string)
        elif isinstance(value, (int, float, bool, str)):
            config[field_name] = value

    return config


def _normalize_entity_selection(entities: list[str] | str) -> str | list[str]:
    """Normalize entity selection to str (single) or list[str] (multiple).

    Single entity selections are stored as strings for backwards compatibility.
    Multiple entity selections are stored as lists for chaining support.
    """
    if isinstance(entities, str):
        return entities
    if len(entities) == 1:
        return entities[0]
    return entities


__all__ = [
    "CHOICE_CONSTANT",
    "CHOICE_DISABLED",
    "CHOICE_ENTITY",
    "boolean_selector_from_field",
    "build_choose_schema_entry",
    "build_choose_selector",
    "build_entity_selector",
    "convert_choose_data_to_config",
    "get_choose_default",
    "get_haeo_input_entity_ids",
    "get_preferred_choice",
    "number_selector_from_field",
    "resolve_haeo_input_entity_id",
]
