"""Core diagnostics collection logic."""

from typing import Any

from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
from custom_components.haeo.const import (
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
from custom_components.haeo.elements import ElementConfigSchema, is_element_config_schema
from custom_components.haeo.entities.haeo_number import ConfigEntityMode, HaeoInputNumber
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
from custom_components.haeo.sensor_utils import get_output_sensors

from .state_provider import StateProvider


def _extract_entity_ids_from_config(config: ElementConfigSchema) -> set[str]:
    """Extract entity IDs from element configuration.

    Entity IDs can be stored as:
    - str: Single entity ID for single-value fields
    - list[str]: Multiple entity IDs for chained forecast/price fields

    This function iterates over all config values and collects entity IDs.
    """
    entity_ids: set[str] = set()
    for value in config.values():
        if isinstance(value, str) and "." in value:
            # Single entity ID string
            entity_ids.add(value)
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            # List of entity IDs (for chained forecasts/prices)
            entity_ids.update(item for item in value if "." in item)
    return entity_ids


async def collect_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    state_provider: StateProvider,
) -> dict[str, Any]:
    """Collect diagnostics using the provided state provider.

    Returns a dict with four main keys:
    - config: HAEO configuration (participants, horizon, period)
    - inputs: Input sensor states used in optimization
    - outputs: Output sensor states from optimization results (omitted for historical)
    - environment: Environment information (HA version, HAEO version, timestamp)

    For editable input entities (constants rather than sensor-driven), the current
    entity value is captured in the participant config. This allows diagnostics
    exports to be used as configuration defaults.

    For historical diagnostics (when state_provider.is_historical is True),
    output sensors are omitted because they reflect the optimization that ran
    at that past time with different inputs.
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

    # Capture current values from editable input entities
    # This allows diagnostics to be used as configuration defaults
    # Only do this for current state (not historical)
    runtime_data = config_entry.runtime_data
    if not state_provider.is_historical and isinstance(runtime_data, HaeoRuntimeData):
        for (element_name, field_name), entity in runtime_data.input_entities.items():
            if element_name not in config["participants"]:
                continue
            participant = config["participants"][element_name]

            # Only capture editable entities (constants, not sensor-driven)
            if entity.entity_mode != ConfigEntityMode.EDITABLE:
                continue

            if isinstance(entity, HaeoInputNumber) and entity.native_value is not None:
                participant[field_name] = entity.native_value
            elif isinstance(entity, HaeoInputSwitch) and entity.is_on is not None:
                participant[field_name] = entity.is_on

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
            extracted_ids = _extract_entity_ids_from_config(participant_config)
            all_entity_ids.update(extracted_ids)

    # Get states using the provider (current or historical)
    entity_states = await state_provider.get_states(sorted(all_entity_ids))

    # Extract input states as dicts
    inputs: list[dict[str, Any]] = [
        state.as_dict() for entity_id in sorted(all_entity_ids) if (state := entity_states.get(entity_id)) is not None
    ]

    # Get output sensors - only for current state, omit for historical
    outputs: dict[str, Any] = {}
    if not state_provider.is_historical:
        outputs = get_output_sensors(hass, config_entry)

    # Get HAEO version from integration metadata
    integration = await async_get_integration(hass, config_entry.domain)
    haeo_version = integration.version or "unknown"

    # Use provider's timestamp if available, otherwise current time
    # Convert to local timezone to ensure offset is included for unambiguous parsing
    timestamp = dt_util.as_local(state_provider.timestamp or dt_util.now()).isoformat()

    # Build environment section
    environment: dict[str, Any] = {
        "ha_version": ha_version,
        "haeo_version": haeo_version,
        "timestamp": timestamp,
        "timezone": str(dt_util.get_default_time_zone()),
        "historical": state_provider.is_historical,
    }

    # Return dict with alphabetically sorted keys
    # This puts config and environment first, then inputs and outputs
    return {
        "config": config,
        "environment": environment,
        "inputs": inputs,
        "outputs": outputs,
    }


__all__ = ["collect_diagnostics"]
