"""Diagnostics support for HAEO integration."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
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
)
from .coordinator import extract_entity_ids_from_config
from .elements import is_element_config_schema
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
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "network":
            raw_data = dict(subentry.data)
            raw_data.setdefault("name", subentry.title)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
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
