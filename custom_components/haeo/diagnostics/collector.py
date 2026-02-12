"""Core diagnostics collection logic."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.coordinator.context import OptimizationContext
from custom_components.haeo.elements import (
    ElementConfigSchema,
    is_element_config_schema,
    set_nested_config_value_by_path,
)
from custom_components.haeo.entities.haeo_number import ConfigEntityMode, HaeoInputNumber
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
from custom_components.haeo.schema import SchemaValue, as_constant_value, is_schema_value
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


def _config_from_context(context: OptimizationContext) -> dict[str, Any]:
    """Build diagnostics config section from OptimizationContext.

    Uses the exact hub configuration and participant schemas the optimizer used,
    rather than re-deriving from the config entry. This captures everything:
    tiers, horizon preset, advanced settings, etc.
    """
    return {
        **dict(context.hub_config),
        "participants": dict(context.participants),
    }


def _inputs_from_context(context: OptimizationContext) -> list[dict[str, Any]]:
    """Build diagnostics inputs section from OptimizationContext.

    Uses the exact source states captured when entities loaded data,
    rather than re-fetching from the state machine.
    """
    return [
        state.as_dict()
        for _entity_id, state in sorted(context.source_states.items())
    ]


def _extract_entity_ids_from_config(config: ElementConfigSchema) -> set[str]:
    """Extract entity IDs from element configuration.

    Entity IDs can be stored as:
    - str: Single entity ID for single-value fields
    - list[str]: Multiple entity IDs for chained forecast/price fields

    This function iterates over all config values and collects entity IDs.
    """

    def _collect(value: SchemaValue | Mapping[str, Any], collected: set[str]) -> None:
        match value:
            case {"type": "entity", "value": entity_ids} if isinstance(entity_ids, list):
                for entity_id in entity_ids:
                    if isinstance(entity_id, str) and "." in entity_id:
                        collected.add(entity_id)
            case {"type": _}:
                return
            case Mapping():
                for nested in value.values():
                    if is_schema_value(nested):
                        _collect(nested, collected)
                    elif isinstance(nested, Mapping):
                        _collect(dict(nested), collected)
            case _:
                return

    entity_ids: set[str] = set()
    _collect(dict(config), entity_ids)
    return entity_ids


async def _config_and_inputs_from_state_provider(
    config_entry: HaeoConfigEntry,
    state_provider: StateProvider,
    runtime_data: HaeoRuntimeData | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Build config and inputs by fetching from config entry and StateProvider.

    Fallback path used for historical diagnostics or when no optimization
    has run yet (no OptimizationContext available).

    Returns:
        Tuple of (config, inputs, missing_entity_ids).

    """
    config: dict[str, Any] = {
        **dict(config_entry.data),
        "participants": {},
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

    return config, inputs, missing_entity_ids


async def _build_environment(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    timestamp: datetime,
    is_historical: bool,
) -> dict[str, Any]:
    """Build the environment section of diagnostics."""
    integration = await async_get_integration(hass, config_entry.domain)
    haeo_version = integration.version or "unknown"

    # Convert to local timezone to ensure offset is included for unambiguous parsing
    environment: dict[str, Any] = {
        "ha_version": ha_version,
        "haeo_version": haeo_version,
        "timestamp": dt_util.as_local(timestamp).isoformat(),
        "timezone": str(dt_util.get_default_time_zone()),
    }

    if is_historical:
        environment["historical"] = True

    return environment


async def collect_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    state_provider: StateProvider,
) -> DiagnosticsResult:
    """Collect diagnostics using the provided state provider.

    Returns a dict with four main keys:
    - config: HAEO configuration (participants, tiers)
    - inputs: Input sensor states used in optimization
    - outputs: Output sensor states from optimization results (omitted for historical)
    - environment: Environment information (HA version, HAEO version, timestamp)

    When OptimizationContext is available (non-historical, optimization has run),
    config and inputs are pulled directly from the context. This faithfully
    represents what the optimizer actually used, not what happens to be in the
    state machine right now.

    For historical diagnostics or when no optimization has run yet, falls back
    to deriving config from the config entry and fetching states via StateProvider.
    """
    runtime_data = config_entry.runtime_data

    # When OptimizationContext is available, use it directly for config and inputs.
    # This captures exactly what the optimizer used for reproducibility.
    coordinator_data = (
        runtime_data.coordinator.data
        if not state_provider.is_historical
        and isinstance(runtime_data, HaeoRuntimeData)
        and runtime_data.coordinator
        else None
    )

    if coordinator_data is not None:
        config = _config_from_context(coordinator_data.context)
        inputs = _inputs_from_context(coordinator_data.context)
        missing_entity_ids: list[str] = []
        timestamp = coordinator_data.started_at
    else:
        # Fallback: derive from config entry and StateProvider
        fallback_runtime = runtime_data if isinstance(runtime_data, HaeoRuntimeData) else None
        config, inputs, missing_entity_ids = await _config_and_inputs_from_state_provider(
            config_entry, state_provider, fallback_runtime
        )
        timestamp = state_provider.timestamp or dt_util.now()

    # Get output sensors - only for current state, omit for historical
    outputs: dict[str, Any] = {}
    if not state_provider.is_historical:
        outputs = get_output_sensors(hass, config_entry)

    environment = await _build_environment(hass, config_entry, timestamp, state_provider.is_historical)

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
