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
from custom_components.haeo.elements import ElementConfigSchema, is_element_config_schema
from custom_components.haeo.schema import SchemaValue, is_schema_value
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


async def _config_and_inputs_for_historical(
    config_entry: HaeoConfigEntry,
    state_provider: StateProvider,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Build config and inputs by fetching from config entry and StateProvider.

    Used for historical diagnostics where we need to fetch states from the
    recorder at a specific point in time.

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

    # Collect input sensor states for all entities used in the configuration
    all_entity_ids: set[str] = set()
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == "network":
            continue
        participant_config = dict(subentry.data)
        participant_config[CONF_ELEMENT_TYPE] = subentry.subentry_type
        if is_element_config_schema(participant_config):
            all_entity_ids.update(_extract_entity_ids_from_config(participant_config))

    # Get states from the recorder at the target time
    entity_states = await state_provider.get_states(sorted(all_entity_ids))

    missing_entity_ids = sorted(all_entity_ids - set(entity_states.keys()))

    inputs: list[dict[str, Any]] = [
        state.as_dict() for entity_id in sorted(all_entity_ids) if (state := entity_states.get(entity_id)) is not None
    ]

    return config, inputs, missing_entity_ids


async def _build_environment(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
) -> dict[str, Any]:
    """Build the environment section of diagnostics.

    Static facts about the runtime — does not vary per invocation.
    """
    integration = await async_get_integration(hass, config_entry.domain)
    haeo_version = integration.version or "unknown"

    return {
        "ha_version": ha_version,
        "haeo_version": haeo_version,
        "timezone": str(dt_util.get_default_time_zone()),
    }


def _to_local_iso(dt: datetime) -> str:
    """Format a datetime as a local-timezone ISO 8601 string."""
    return dt_util.as_local(dt).isoformat()


async def collect_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    state_provider: StateProvider,
) -> DiagnosticsResult:
    """Collect diagnostics using the provided state provider.

    Returns a dict with five main keys:
    - config: HAEO configuration (hub settings, participants)
    - environment: Static runtime info (HA version, HAEO version, timezone)
    - inputs: Input sensor states used in optimization
    - info: Per-snapshot context (timestamps, historical flag)
    - outputs: Output sensor states from optimization results (omitted for historical)

    Two modes:
    - Historical: fetches config from the config entry and states from the recorder.
    - Current: pulls config and inputs from OptimizationContext (what the optimizer
      actually used). Requires at least one optimization to have completed.

    Raises:
        RuntimeError: If non-historical and no optimization has run yet.

    """
    if state_provider.is_historical:
        config, inputs, missing_entity_ids = await _config_and_inputs_for_historical(
            config_entry, state_provider
        )
        timestamp = state_provider.timestamp or dt_util.now()
        info: dict[str, Any] = {
            "historical": True,
            "timestamp": _to_local_iso(timestamp),
        }
    else:
        runtime_data = config_entry.runtime_data
        if (
            not isinstance(runtime_data, HaeoRuntimeData)
            or not runtime_data.coordinator
            or not runtime_data.coordinator.data
        ):
            msg = "Cannot collect diagnostics: no optimization has completed yet"
            raise RuntimeError(msg)

        coordinator_data = runtime_data.coordinator.data
        config = _config_from_context(coordinator_data.context)
        inputs = _inputs_from_context(coordinator_data.context)
        missing_entity_ids = []
        info = {
            "historical": False,
            "horizon_start": _to_local_iso(coordinator_data.context.horizon_start),
            "started_at": _to_local_iso(coordinator_data.started_at),
            "completed_at": _to_local_iso(coordinator_data.completed_at),
        }

    environment = await _build_environment(hass, config_entry)

    data: dict[str, Any] = {
        "config": config,
        "environment": environment,
        "inputs": inputs,
        "info": info,
    }
    if not state_provider.is_historical:
        data["outputs"] = get_output_sensors(hass, config_entry)

    return DiagnosticsResult(
        data=data,
        missing_entity_ids=missing_entity_ids,
    )


__all__ = ["DiagnosticsResult", "collect_diagnostics"]
