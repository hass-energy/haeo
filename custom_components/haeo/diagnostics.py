"""Diagnostics support for HAEO integration."""

import contextlib
from typing import Any, NotRequired, Required, get_args, get_origin, get_type_hints

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ELEMENT_TYPE,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DOMAIN,
)
from .coordinator import extract_entity_ids_from_config
from .elements import ELEMENT_TYPES, is_element_config_schema
from .schema.fields import BooleanFieldMeta, FieldMeta
from .sensor_utils import get_output_sensors


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a HAEO config entry.

    Returns a dict with four main keys:
    - config: HAEO configuration (participants, horizon, period)
    - inputs: Input sensor states used in optimization
    - outputs: Output sensor states from optimization results
    - environment: Environment information (HA version, HAEO version, timestamp)
    """
    # Build config section with participants
    config: dict[str, Any] = {
        "participants": {},
        CONF_TIER_1_COUNT: config_entry.data.get(CONF_TIER_1_COUNT),
        CONF_TIER_1_DURATION: config_entry.data.get(CONF_TIER_1_DURATION),
        CONF_TIER_2_COUNT: config_entry.data.get(CONF_TIER_2_COUNT),
        CONF_TIER_2_DURATION: config_entry.data.get(CONF_TIER_2_DURATION),
        CONF_TIER_3_COUNT: config_entry.data.get(CONF_TIER_3_COUNT),
        CONF_TIER_3_DURATION: config_entry.data.get(CONF_TIER_3_DURATION),
        CONF_TIER_4_COUNT: config_entry.data.get(CONF_TIER_4_COUNT),
        CONF_TIER_4_DURATION: config_entry.data.get(CONF_TIER_4_DURATION),
    }

    # Transform subentries into participants dict
    # For fields using config entities (number/switch), capture current state values
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "network":
            raw_data = dict(subentry.data)
            raw_data.setdefault("name", subentry.title)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)

            # Check for config entity fields and capture their current state
            element_type = subentry.subentry_type
            if element_type in ELEMENT_TYPES:
                registry_entry = ELEMENT_TYPES[element_type]
                type_hints = get_type_hints(registry_entry.schema, include_extras=True)

                for field_name, field_type in type_hints.items():
                    # Unwrap NotRequired/Required
                    origin = get_origin(field_type)
                    unwrapped_type = get_args(field_type)[0] if origin in (NotRequired, Required) else field_type

                    if not hasattr(unwrapped_type, "__metadata__"):
                        continue

                    field_meta = next((m for m in unwrapped_type.__metadata__ if isinstance(m, FieldMeta)), None)
                    if not field_meta:
                        continue

                    # Skip fields that don't create entities
                    if (
                        not isinstance(field_meta, BooleanFieldMeta)
                        and field_meta.min is None
                        and field_meta.max is None
                        and field_meta.step is None
                        and field_meta.unit is None
                    ):
                        continue

                    field_value = subentry.data.get(field_name)

                    # If not a string/list of strings, this field uses a config entity
                    # (i.e., it's a static value or None, meaning Editable mode)
                    is_entity_provided = isinstance(field_value, str) or (
                        isinstance(field_value, list) and field_value and isinstance(field_value[0], str)
                    )

                    if not is_entity_provided:
                        # Look up the input entity's current state
                        platform = "switch" if isinstance(field_meta, BooleanFieldMeta) else "number"
                        entity_registry = er.async_get(hass)
                        unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_name}"
                        entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)
                        if entity_id:
                            state = hass.states.get(entity_id)
                            if state is not None:
                                # Store the current state value in the config
                                if platform == "number":
                                    with contextlib.suppress(ValueError, TypeError):
                                        raw_data[field_name] = float(state.state)
                                else:
                                    # Switch - store as boolean
                                    raw_data[field_name] = state.state == "on"

            config["participants"][subentry.title] = raw_data

    # Collect input sensor states for all entities used in the configuration
    all_entity_ids: set[str] = set()
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == "network":
            continue
        # Create config dict with element_type
        participant_config = dict(subentry.data)
        participant_config[CONF_ELEMENT_TYPE] = subentry.subentry_type
        # Extract entity IDs from valid element configs only
        if is_element_config_schema(participant_config):
            extracted_ids = extract_entity_ids_from_config(participant_config)
            all_entity_ids.update(extracted_ids)

    # Extract input states as dicts
    inputs: list[dict[str, Any]] = [
        state.as_dict() for entity_id in sorted(all_entity_ids) if (state := hass.states.get(entity_id)) is not None
    ]

    # Get output sensors using common utility function
    # This filters to entities created by this config entry and cleans unstable fields
    outputs = get_output_sensors(hass, config_entry)

    # Get HAEO version from integration metadata
    integration = await async_get_integration(hass, config_entry.domain)
    haeo_version = integration.version or "unknown"

    # Build environment section
    environment: dict[str, Any] = {
        "ha_version": ha_version,
        "haeo_version": haeo_version,
        "timestamp": dt_util.now().isoformat(),
        "timezone": str(dt_util.get_default_time_zone()),
    }

    # Return dict with alphabetically sorted keys
    # This puts config and environment first, then inputs and outputs
    return {
        "config": config,
        "environment": environment,
        "inputs": inputs,
        "outputs": outputs,
    }
