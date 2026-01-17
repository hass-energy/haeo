"""Shared utilities for building element config flows with choose selectors.

This module provides utilities for the unified config flow pattern using
Home Assistant's ChooseSelector, allowing users to pick between "Entity"
(select from compatible sensors) or "Constant" (enter a value directly).
"""

from collections.abc import Collection, Mapping
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
CHOICE_NONE = "none"


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
    current_data: Mapping[str, Any] | None = None,
    *,
    is_optional: bool = False,
) -> str:
    """Determine which choice should be first in the ChooseSelector.

    The ChooseSelector always selects the first choice, so we order
    choices based on what should be pre-selected.

    Args:
        field_info: Input field metadata.
        current_data: Current configuration data (for reconfigure).
        is_optional: Whether the field is optional (enables "none" choice).

    Returns:
        CHOICE_ENTITY, CHOICE_CONSTANT, or CHOICE_NONE based on context.

    """
    field_name = field_info.field_name

    # Reconfigure: infer from stored value
    if current_data is not None:
        if field_name in current_data:
            value = current_data[field_name]
            return CHOICE_ENTITY if isinstance(value, (str, list)) else CHOICE_CONSTANT
        if is_optional:
            return CHOICE_NONE  # Field was explicitly omitted

    # New entry: check for explicit default mode
    if field_info.defaults and field_info.defaults.mode:
        return CHOICE_CONSTANT if field_info.defaults.mode == "value" else CHOICE_ENTITY

    # Fallback: optional -> none, required -> entity
    return CHOICE_NONE if is_optional else CHOICE_ENTITY


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
    is_optional: bool = False,
    include_entities: list[str] | None = None,
    multiple: bool = True,
    preferred_choice: str = CHOICE_ENTITY,
) -> Any:
    """Build a ChooseSelector allowing user to pick Entity, Constant, or Disabled.

    Args:
        field_info: Input field metadata.
        is_optional: Whether the field is optional (adds "none" choice).
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
    none_selector = ConstantSelector(ConstantSelectorConfig(value=""))
    none_choice = ChooseSelectorChoiceConfig(selector=none_selector.serialize()["selector"])

    # Canonical order and mapping of choices
    choice_order = [CHOICE_ENTITY, CHOICE_CONSTANT, CHOICE_NONE]
    choice_map = {
        CHOICE_ENTITY: entity_choice,
        CHOICE_CONSTANT: constant_choice,
        CHOICE_NONE: none_choice,
    }

    if not is_optional:
        choice_order.remove(CHOICE_NONE)
        del choice_map[CHOICE_NONE]

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
    include_entities: list[str] | None = None,
    multiple: bool = True,
    preferred_choice: str = CHOICE_ENTITY,
) -> tuple[vol.Marker, Any]:
    """Build a schema entry using NormalizingChooseSelector.

    Args:
        field_info: Input field metadata.
        is_optional: Whether the field is optional (adds "none" choice).
        include_entities: Entity IDs to include (compatible entities from unit filtering).
        multiple: Whether to allow multiple entity selection.
        preferred_choice: Which choice should appear first (will be pre-selected).

    Returns:
        Tuple of (vol.Required/Optional marker, NormalizingChooseSelector).

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
        Config dict with:
        - Constant fields: stored as float/bool
        - Entity fields with single entity: stored as str
        - Entity fields with multiple entities: stored as list[str]
        - None/Disabled fields: omitted

    """
    config: dict[str, Any] = {}
    field_names = set(input_fields)

    for field_name, value in user_input.items():
        if field_name in exclude_keys:
            continue
        if field_name not in field_names:
            continue

        # Skip None values (disabled/none choice)
        if value is None:
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
    optional_keys: frozenset[str],
    *,
    exclude_fields: Collection[str] = (),
) -> dict[str, str]:
    """Validate that required choose fields have valid selections.

    Args:
        user_input: User input dictionary from the form.
        input_fields: Mapping of InputFieldInfo defining the fields.
        optional_keys: The __optional_keys__ frozenset from the TypedDict schema.
        exclude_fields: Field names to skip validation for.

    Returns:
        Dictionary of field_name -> error_key for invalid fields.

    """
    errors: dict[str, str] = {}

    for field_name, field_info in input_fields.items():
        if field_name in exclude_fields:
            continue

        is_optional = field_name in optional_keys and not field_info.force_required

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
    "boolean_selector_from_field",
    "build_choose_schema_entry",
    "build_choose_selector",
    "build_entity_selector",
    "convert_choose_data_to_config",
    "get_choose_default",
    "get_haeo_input_entity_ids",
    "get_preferred_choice",
    "is_valid_choose_value",
    "number_selector_from_field",
    "preprocess_choose_selector_input",
    "resolve_haeo_input_entity_id",
    "validate_choose_fields",
]
