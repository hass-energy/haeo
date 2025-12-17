"""Config entity mode resolver."""

from typing import NotRequired, get_origin, get_type_hints

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements import ELEMENT_TYPES

from .mode import ConfigEntityMode


def get_config_entity_unique_id(
    entry_id: str,
    subentry_id: str,
    input_name: str,
) -> str:
    """Get the unique ID for a config entity.

    Args:
        entry_id: The config entry ID.
        subentry_id: The subentry ID for the element.
        input_name: The input name (e.g., 'battery_capacity', 'grid_price_import').

    Returns:
        The unique ID in format "{entry_id}_{subentry_id}_{input_name}".

    """
    return f"{entry_id}_{subentry_id}_{input_name}"


def get_config_entity_id(
    hass: HomeAssistant,
    entry_id: str,
    subentry_id: str,
    input_name: str,
    *,
    platform: str = "number",
) -> str | None:
    """Get the entity ID for a config entity.

    Args:
        hass: Home Assistant instance.
        entry_id: The config entry ID.
        subentry_id: The subentry ID for the element.
        input_name: The input name.
        platform: The platform ("number" or "switch").

    Returns:
        The entity ID if found, None otherwise.

    """
    entity_registry = er.async_get(hass)
    unique_id = get_config_entity_unique_id(entry_id, subentry_id, input_name)
    return entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)


def is_config_entity_enabled(
    hass: HomeAssistant,
    entry_id: str,
    subentry_id: str,
    input_name: str,
    *,
    platform: str = "number",
) -> bool:
    """Check if a config entity is enabled.

    Args:
        hass: Home Assistant instance.
        entry_id: The config entry ID.
        subentry_id: The subentry ID for the element.
        input_name: The input name.
        platform: The platform ("number" or "switch").

    Returns:
        True if the entity exists and is enabled, False otherwise.

    """
    entity_registry = er.async_get(hass)
    entity_id = get_config_entity_id(hass, entry_id, subentry_id, input_name, platform=platform)
    if entity_id is None:
        return False

    entry = entity_registry.async_get(entity_id)
    return entry is not None and entry.disabled_by is None


def resolve_config_entity_mode(
    hass: HomeAssistant,
    entry_id: str,
    subentry_id: str,
    input_name: str,
    configured_value: str | list[str] | None,
    *,
    platform: str = "number",
) -> ConfigEntityMode:
    """Determine the operating mode for a config entity.

    Args:
        hass: Home Assistant instance.
        entry_id: The config entry ID.
        subentry_id: The subentry ID for the element.
        input_name: The input name.
        configured_value: The value configured in the config flow (entity ID(s) or None).
        platform: The platform ("number" or "switch").

    Returns:
        The config entity mode.

    """
    # If user provided an entity in config → Driven mode
    if configured_value is not None:
        # Handle both single entity ID and list of entity IDs
        has_entities = (isinstance(configured_value, list) and len(configured_value) > 0) or (
            isinstance(configured_value, str) and configured_value != ""
        )
        if has_entities:
            return ConfigEntityMode.DRIVEN

    # User didn't provide entities - check if config entity is enabled
    if is_config_entity_enabled(hass, entry_id, subentry_id, input_name, platform=platform):
        return ConfigEntityMode.EDITABLE

    return ConfigEntityMode.DISABLED


def is_input_required(element_type: str, input_name: str) -> bool:
    """Check if an input field is required (not optional).

    Args:
        element_type: The element type.
        input_name: The input name.

    Returns:
        True if the field is required, False if optional.

    """
    if element_type not in ELEMENT_TYPES:
        return False

    registry_entry = ELEMENT_TYPES[element_type]
    schema_cls = registry_entry.schema

    # Extract field name from input name (e.g. battery_capacity -> capacity)
    prefix = f"{element_type}_"
    if not input_name.startswith(prefix):
        return False

    field_name = input_name[len(prefix) :]

    type_hints = get_type_hints(schema_cls, include_extras=True)
    if field_name not in type_hints:
        return False

    field_type = type_hints[field_name]

    # Check for NotRequired
    origin = get_origin(field_type)
    if origin is NotRequired:
        return False

    # Also check defaults - if a default exists, it's not strictly required from user
    return field_name not in registry_entry.defaults


def resolve_entity_to_load(
    hass: HomeAssistant,
    entry_id: str,
    subentry_id: str,
    element_type: str,
    input_name: str,
    configured_value: str | list[str] | None,
    *,
    platform: str = "number",
) -> str | list[str] | None:
    """Resolve which entity or entities to load data from.

    Based on the configured value and config entity mode, determine the
    entity ID(s) to load data from:

    - Driven mode: Load from the configured external entity/entities
    - Editable mode: Load from the config number/switch entity
    - Disabled mode: Return None (field is not active)

    Args:
        hass: Home Assistant instance.
        entry_id: The config entry ID.
        subentry_id: The subentry ID for the element.
        element_type: The element type (e.g., 'battery', 'grid').
        input_name: The input name.
        configured_value: The value configured in the config flow.
        platform: The platform ("number" or "switch").

    Returns:
        Entity ID(s) to load from, or None if field is disabled.

    Raises:
        ValueError: If a required field is in disabled mode.

    """
    mode = resolve_config_entity_mode(hass, entry_id, subentry_id, input_name, configured_value, platform=platform)

    if mode == ConfigEntityMode.DRIVEN:
        # Load from configured external entities
        return configured_value

    if mode == ConfigEntityMode.EDITABLE:
        # Load from the config entity
        config_entity_id = get_config_entity_id(hass, entry_id, subentry_id, input_name, platform=platform)
        if config_entity_id is None:
            # Config entity not yet registered - this can happen during setup
            # Return None and caller should handle this case
            return None
        return config_entity_id

    # Disabled mode
    if is_input_required(element_type, input_name):
        msg = (
            f"Required input '{input_name}' on element type '{element_type}' "
            "is disabled. Enable the config entity or provide an external entity."
        )
        raise ValueError(msg)

    return None
