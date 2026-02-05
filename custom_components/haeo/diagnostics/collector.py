"""Core diagnostics collection logic."""

from collections.abc import Mapping
from dataclasses import dataclass
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
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
)
from custom_components.haeo.elements import (
    ElementConfigSchema,
    is_element_config_schema,
    set_nested_config_value_by_path,
)
from custom_components.haeo.entities.haeo_number import ConfigEntityMode, HaeoInputNumber
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
from custom_components.haeo.flows import HUB_SECTION_TIERS
from custom_components.haeo.schema import SchemaContainer, SchemaValue, as_constant_value
from custom_components.haeo.sections import SECTION_COMMON
from custom_components.haeo.sensor_utils import get_output_sensors

from .state_provider import StateProvider


@dataclass
class DiagnosticsResult:
    """Result of collecting diagnostics."""

    data: dict[str, Any]
    """The diagnostics data to be saved."""

    missing_entity_ids: list[str]
    """Entity IDs that were expected but not found in state provider."""


def _extract_entity_ids_from_config(config: ElementConfigSchema) -> set[str]:
    """Extract entity IDs from element configuration.

    Entity IDs can be stored as:
    - str: Single entity ID for single-value fields
    - list[str]: Multiple entity IDs for chained forecast/price fields

    This function iterates over all config values and collects entity IDs.
    """

    def _collect(value: SchemaValue | SchemaContainer, collected: set[str]) -> None:
        match value:
            case {"type": "entity", "value": entity_ids}:
                for entity_id in entity_ids:
                    if "." in entity_id:
                        collected.add(entity_id)
            case {"type": _}:
                return
            case Mapping():
                for nested in value.values():
                    _collect(nested, collected)
            case _:
                return

    entity_ids: set[str] = set()
    _collect(config, entity_ids)
    return entity_ids


async def collect_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    state_provider: StateProvider,
) -> DiagnosticsResult:
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
    tiers_section = config_entry.data.get(HUB_SECTION_TIERS)
    tiers = tiers_section if isinstance(tiers_section, dict) else {}
    config: dict[str, Any] = {
        "participants": {},
        HUB_SECTION_TIERS: {
            CONF_TIER_1_COUNT: tiers.get(CONF_TIER_1_COUNT, DEFAULT_TIER_1_COUNT),
            CONF_TIER_1_DURATION: tiers.get(CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION),
            CONF_TIER_2_COUNT: tiers.get(CONF_TIER_2_COUNT, DEFAULT_TIER_2_COUNT),
            CONF_TIER_2_DURATION: tiers.get(CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION),
            CONF_TIER_3_COUNT: tiers.get(CONF_TIER_3_COUNT, DEFAULT_TIER_3_COUNT),
            CONF_TIER_3_DURATION: tiers.get(CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION),
            CONF_TIER_4_COUNT: tiers.get(CONF_TIER_4_COUNT, DEFAULT_TIER_4_COUNT),
            CONF_TIER_4_DURATION: tiers.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION),
        },
    }

    # Transform subentries into participants dict
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "network":
            raw_data = dict(subentry.data)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            common = raw_data.get(SECTION_COMMON)
            if isinstance(common, dict):
                common.setdefault("name", subentry.title)
            else:
                raw_data.setdefault("name", subentry.title)
            config["participants"][subentry.title] = raw_data

    # Capture current values from editable input entities
    # This allows diagnostics to be used as configuration defaults
    # Only do this for current state (not historical)
    runtime_data = config_entry.runtime_data
    if not state_provider.is_historical and isinstance(runtime_data, HaeoRuntimeData):
        for (element_name, field_path), entity in runtime_data.input_entities.items():
            if element_name not in config["participants"]:
                continue
            participant = config["participants"][element_name]

            # Only capture editable entities (constants, not sensor-driven)
            if entity.entity_mode != ConfigEntityMode.EDITABLE:
                continue

            if isinstance(entity, HaeoInputNumber) and entity.native_value is not None:
                set_nested_config_value_by_path(participant, field_path, as_constant_value(entity.native_value))
            elif isinstance(entity, HaeoInputSwitch) and entity.is_on is not None:
                set_nested_config_value_by_path(participant, field_path, as_constant_value(entity.is_on))

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

    # Calculate which entities were expected but not found
    missing_entity_ids = sorted(all_entity_ids - set(entity_states.keys()))

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
    }

    if state_provider.is_historical:
        environment["historical"] = True

    # Return result with data and missing entity info
    return DiagnosticsResult(
        data={
            "config": config,
            "environment": environment,
            "inputs": inputs,
            "outputs": outputs,
        },
        missing_entity_ids=missing_entity_ids,
    )


__all__ = ["DiagnosticsResult", "collect_diagnostics"]
