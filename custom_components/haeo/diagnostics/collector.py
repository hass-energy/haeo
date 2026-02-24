"""Core diagnostics collection logic."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from homeassistant.components.recorder import history as recorder_history
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance as get_recorder_instance
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
from custom_components.haeo.const import ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.context import OptimizationContext
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import SchemaValue, is_schema_value
from custom_components.haeo.core.schema.elements import ElementConfigSchema
from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.sensor_utils import (
    SensorStateDict,
    get_duration_sensor_entity_id,
    get_horizon_sensor_entity_id,
    get_output_sensors,
)


@dataclass(frozen=True, slots=True)
class DiagnosticsInfo:
    """Timestamps and context for a diagnostics snapshot."""

    diagnostic_request_time: str
    """Wall-clock time when the diagnostic was requested (ISO 8601)."""

    diagnostic_target_time: str | None
    """The historical time the user asked for (ISO 8601, None for current diagnostics)."""

    optimization_start_time: str
    """When the optimization run started (ISO 8601)."""

    optimization_end_time: str
    """When the optimization run completed (ISO 8601)."""

    horizon_start: str
    """Aligned start of the forecast window (ISO 8601)."""


@dataclass(frozen=True, slots=True)
class EnvironmentInfo:
    """Static runtime environment facts."""

    ha_version: str
    """Home Assistant version."""

    haeo_version: str
    """HAEO integration version."""

    timezone: str
    """System timezone."""


@dataclass(frozen=True, slots=True)
class DiagnosticsResult:
    """Result of collecting diagnostics."""

    config: dict[str, Any]
    """HAEO configuration (hub settings, participants)."""

    environment: EnvironmentInfo
    """Static runtime info (HA version, HAEO version, timezone)."""

    inputs: list[dict[str, Any]]
    """Input sensor states used in optimization."""

    info: DiagnosticsInfo
    """Per-snapshot context (timestamps, horizon)."""

    outputs: dict[str, SensorStateDict] | None
    """Output sensor states (None for historical diagnostics)."""

    missing_entity_ids: tuple[str, ...]
    """Entity IDs that were expected but not found in the recorder."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict for HA diagnostics output."""
        data: dict[str, Any] = {
            "environment": asdict(self.environment),
            "info": asdict(self.info),
            "config": self.config,
            "inputs": self.inputs,
        }
        if self.outputs is not None:
            data["outputs"] = self.outputs
        return data


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
    return [state.as_dict() for _entity_id, state in sorted(context.source_states.items())]


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
        if subentry.subentry_type != ELEMENT_TYPE_NETWORK:
            raw_data = dict(subentry.data)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            raw_data.setdefault(CONF_NAME, subentry.title)
            config["participants"][subentry.title] = raw_data

    return config


def _collect_entity_ids_from_entry(config_entry: HaeoConfigEntry) -> set[str]:
    """Collect all input entity IDs referenced in config entry subentries."""
    all_entity_ids: set[str] = set()
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == ELEMENT_TYPE_NETWORK:
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
            end_time=target_time,
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
    target_time: datetime,
) -> tuple[datetime, datetime, str] | None:
    """Find the last optimization run that completed at or before a given time.

    Uses the recorder to look up the optimization_duration sensor's state
    at the target time. The sensor's last_updated is when the run completed,
    and its state is the duration in seconds. Then fetches the horizon sensor
    state at the inferred started_at.

    Returns:
        Tuple of (started_at, completed_at, horizon_start) or None if no run found.

    """
    duration_entity_id = get_duration_sensor_entity_id(hass, config_entry)
    if duration_entity_id is None:
        return None

    horizon_entity_id = get_horizon_sensor_entity_id(hass, config_entry)
    if horizon_entity_id is None:
        return None

    recorder = get_recorder_instance(hass)

    def _query() -> dict[str, list[State]]:
        result = recorder_history.get_significant_states(
            hass,
            start_time=target_time,
            end_time=target_time,
            entity_ids=[duration_entity_id, horizon_entity_id],
            include_start_time_state=True,
            significant_changes_only=False,
            no_attributes=False,
        )
        return cast("dict[str, list[State]]", result)

    states = await recorder.async_add_executor_job(_query)

    duration_list = states.get(duration_entity_id, [])
    if not duration_list:
        return None

    # include_start_time_state gives us the state at or before target_time first
    duration_state = duration_list[0]

    try:
        duration_seconds = float(duration_state.state)
    except (ValueError, TypeError):
        return None

    completed_at = duration_state.last_updated
    started_at = completed_at - timedelta(seconds=duration_seconds)

    horizon_list = states.get(horizon_entity_id, [])
    if not horizon_list:
        return None

    return started_at, completed_at, horizon_list[0].state


async def _build_environment(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
) -> EnvironmentInfo:
    """Build the environment section of diagnostics.

    Static facts about the runtime — does not vary per invocation.
    """
    integration = await async_get_integration(hass, config_entry.domain)
    haeo_version = integration.version or "unknown"

    return EnvironmentInfo(
        ha_version=ha_version,
        haeo_version=haeo_version,
        timezone=str(dt_util.get_default_time_zone()),
    )


def _to_local_iso(dt: datetime) -> str:
    """Format a datetime as a local-timezone ISO 8601 string."""
    return dt_util.as_local(dt).isoformat()


async def collect_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    *,
    target_time: datetime | None = None,
) -> DiagnosticsResult:
    """Collect diagnostics for a config entry.

    Two modes:
    - Current (target_time is None): pulls config and inputs from OptimizationContext
      (what the optimizer actually used). Requires at least one optimization
      to have completed.
    - Historical (target_time provided): finds the last optimization run that
      completed at or before target_time, fetches inputs from the recorder at that
      run's start time. Config is always current.

    Raises:
        RuntimeError: If no optimization has run (current) or no run found
            before the requested time (historical).

    """
    now = _to_local_iso(dt_util.utcnow())

    if target_time is not None:
        run = await _get_last_run_before(hass, config_entry, target_time)
        if run is None:
            msg = "Cannot collect diagnostics: no optimization run found before the requested time"
            raise RuntimeError(msg)

        started_at, completed_at, horizon_start = run
        config = _config_from_entry(config_entry)
        inputs, missing = await _fetch_inputs_at(hass, config_entry, started_at)
        info = DiagnosticsInfo(
            diagnostic_request_time=now,
            diagnostic_target_time=_to_local_iso(target_time),
            optimization_start_time=_to_local_iso(started_at),
            optimization_end_time=_to_local_iso(completed_at),
            horizon_start=horizon_start,
        )
        outputs = None
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
        missing = []
        info = DiagnosticsInfo(
            diagnostic_request_time=now,
            diagnostic_target_time=None,
            optimization_start_time=_to_local_iso(coordinator_data.started_at),
            optimization_end_time=_to_local_iso(coordinator_data.completed_at),
            horizon_start=_to_local_iso(coordinator_data.context.horizon_start),
        )
        outputs = get_output_sensors(hass, config_entry)

    environment = await _build_environment(hass, config_entry)

    return DiagnosticsResult(
        config=config,
        environment=environment,
        inputs=inputs,
        info=info,
        outputs=outputs,
        missing_entity_ids=tuple(missing),
    )


__all__ = ["DiagnosticsInfo", "DiagnosticsResult", "EnvironmentInfo", "collect_diagnostics"]
