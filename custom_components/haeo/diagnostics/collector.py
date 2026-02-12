"""Core diagnostics collection logic."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from homeassistant.components.recorder import history as recorder_history
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance as get_recorder_instance
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.coordinator.context import OptimizationContext
from custom_components.haeo.elements import ElementConfigSchema, is_element_config_schema
from custom_components.haeo.schema import SchemaValue, is_schema_value
from custom_components.haeo.sections import SECTION_COMMON
from custom_components.haeo.sensor_utils import get_duration_sensor_entity_id, get_output_sensors

# How far back to search for the last optimization run in the recorder
_LOOKBACK = timedelta(days=30)


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


def _config_from_entry(config_entry: HaeoConfigEntry) -> dict[str, Any]:
    """Build diagnostics config section from the config entry (current config).

    Used for historical diagnostics where we always use the current configuration.
    """
    config: dict[str, Any] = {
        **dict(config_entry.data),
        "participants": {},
    }

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

    return config


def _collect_entity_ids_from_entry(config_entry: HaeoConfigEntry) -> set[str]:
    """Collect all input entity IDs referenced in config entry subentries."""
    all_entity_ids: set[str] = set()
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == "network":
            continue
        participant_config = dict(subentry.data)
        participant_config[CONF_ELEMENT_TYPE] = subentry.subentry_type
        if is_element_config_schema(participant_config):
            all_entity_ids.update(_extract_entity_ids_from_config(participant_config))
    return all_entity_ids


async def _fetch_inputs_at(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    target_time: datetime,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Fetch input entity states from the recorder at a specific time.

    Returns:
        Tuple of (inputs, missing_entity_ids).

    """
    all_entity_ids = _collect_entity_ids_from_entry(config_entry)
    if not all_entity_ids:
        return [], []

    recorder = get_recorder_instance(hass)
    entity_id_list = sorted(all_entity_ids)

    def _query() -> dict[str, list[State]]:
        result = recorder_history.get_significant_states(
            hass,
            start_time=target_time,
            end_time=target_time + timedelta(seconds=1),
            entity_ids=entity_id_list,
            include_start_time_state=True,
            significant_changes_only=False,
            no_attributes=False,
        )
        return cast("dict[str, list[State]]", result)

    states = await recorder.async_add_executor_job(_query)
    entity_states = {eid: slist[0] for eid, slist in states.items() if slist}

    missing_entity_ids = sorted(all_entity_ids - set(entity_states.keys()))
    inputs: list[dict[str, Any]] = [
        state.as_dict() for eid in entity_id_list if (state := entity_states.get(eid)) is not None
    ]
    return inputs, missing_entity_ids


async def _get_last_run_before(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    before_time: datetime,
) -> tuple[datetime, datetime] | None:
    """Find the last optimization run that completed at or before a given time.

    Uses the recorder to look up the optimization_duration sensor's state
    at the target time. The sensor's last_updated is when the run completed,
    and its state is the duration in seconds.

    Returns:
        Tuple of (started_at, completed_at) or None if no run found.

    """
    duration_entity_id = get_duration_sensor_entity_id(hass, config_entry)
    if duration_entity_id is None:
        return None

    recorder = get_recorder_instance(hass)

    def _query() -> dict[str, list[State]]:
        result = recorder_history.get_significant_states(
            hass,
            start_time=before_time - _LOOKBACK,
            end_time=before_time + timedelta(seconds=1),
            entity_ids=[duration_entity_id],
            include_start_time_state=True,
            significant_changes_only=False,
            no_attributes=False,
        )
        return cast("dict[str, list[State]]", result)

    states = await recorder.async_add_executor_job(_query)

    state_list = states.get(duration_entity_id, [])
    if not state_list:
        return None

    # Take the most recent state (last in the list)
    last_state = state_list[-1]

    try:
        duration_seconds = float(last_state.state)
    except (ValueError, TypeError):
        return None

    completed_at = last_state.last_updated
    started_at = completed_at - timedelta(seconds=duration_seconds)
    return started_at, completed_at


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
    *,
    as_of: datetime | None = None,
) -> DiagnosticsResult:
    """Collect diagnostics for a config entry.

    Returns a dict with these keys:
    - config: HAEO configuration (hub settings, participants)
    - environment: Static runtime info (HA version, HAEO version, timezone)
    - inputs: Input sensor states used in optimization
    - info: Per-snapshot context (timestamps; as_of_timestamp when historical)
    - outputs: Output sensor states (current only)

    Two modes:
    - Current (as_of is None): pulls config and inputs from OptimizationContext
      (what the optimizer actually used). Requires at least one optimization
      to have completed.
    - Historical (as_of provided): finds the last optimization run that
      completed at or before as_of, fetches inputs from the recorder at that
      run's start time. Config is always current.

    Raises:
        RuntimeError: If no optimization has run (current) or no run found
            before the requested time (historical).

    """
    if as_of is not None:
        run = await _get_last_run_before(hass, config_entry, as_of)
        if run is None:
            msg = "Cannot collect diagnostics: no optimization run found before the requested time"
            raise RuntimeError(msg)

        started_at, completed_at = run
        config = _config_from_entry(config_entry)
        inputs, missing_entity_ids = await _fetch_inputs_at(hass, config_entry, started_at)
        info: dict[str, Any] = {
            "as_of_timestamp": _to_local_iso(as_of),
            "started_at": _to_local_iso(started_at),
            "completed_at": _to_local_iso(completed_at),
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
        # horizon_start: aligned start of the forecast window (from HorizonManager, updated at
        # period boundaries). started_at/completed_at: wall-clock when this run actually ran.
        info = {
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
    if as_of is None:
        data["outputs"] = get_output_sensors(hass, config_entry)

    return DiagnosticsResult(
        data=data,
        missing_entity_ids=missing_entity_ids,
    )


__all__ = ["DiagnosticsResult", "collect_diagnostics"]
