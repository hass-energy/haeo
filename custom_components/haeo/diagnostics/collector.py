"""Core diagnostics collection logic."""

import asyncio
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Final

from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance as get_recorder_instance
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
from custom_components.haeo.const import ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.annotated_state import AnnotatedState
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.context import OptimizationContext
from custom_components.haeo.core.data.loader.calendar import (
    CALENDAR_EVENTS_ATTRIBUTE,
    CalendarEventDict,
    load_calendar_events,
    open_window_start,
)
from custom_components.haeo.core.data.loader.config_loader import configured_value, element_inputs, input_value
from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE, totals_since
from custom_components.haeo.core.schema import SchemaValue, is_schema_value
from custom_components.haeo.core.schema.elements import ElementConfigSchema
from custom_components.haeo.core.schema.entity_value import is_entity_value
from custom_components.haeo.diagnostics.recorder_history import get_significant_states_full
from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.inputs.calendar_loader import async_fetch_calendar_events
from custom_components.haeo.inputs.meter_history import async_meter_totals_at
from custom_components.haeo.sensor_utils import (
    SensorStateDict,
    get_duration_sensor_entity_id,
    get_horizon_sensor_entity_id,
    get_output_sensors,
)

"""Schema version of the serialized diagnostics output. Bump on breaking shape changes."""
# Keys to redact from diagnostics output. Following HA convention, ``async_redact_data``
# is also responsible for unwrapping ``MappingProxyType`` (HA's wrapper around
# ``ConfigEntry.data`` / ``ConfigSubentry.data``) into plain dicts as a side-effect of
# its ``{**data}`` recursion -- without that, ``ExtendedJSONEncoder`` falls back to
# ``{"__type": ..., "repr": ...}`` placeholders for those values.
_REDACTED_CONFIG_KEYS: frozenset[str] = frozenset()
DIAGNOSTICS_SCHEMA_VERSION = 2


# Calendar events fetched for a historical run reach past the longest horizon preset;
# events beyond the replayed horizon are ignored when it resolves them.
HISTORICAL_CALENDAR_LOOKAHEAD: Final = timedelta(days=8)


@dataclass(frozen=True, slots=True)
class EnvironmentInfo:
    """Runtime environment facts and per-snapshot timing for a diagnostics capture."""

    diagnostics_version: int
    """Schema version of the serialized diagnostics output. Bump on breaking shape changes."""

    ha_version: str
    """Home Assistant version."""

    haeo_version: str
    """HAEO integration version."""

    timezone: str
    """System timezone."""

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
class DiagnosticsResult:
    """Result of collecting diagnostics."""

    config: dict[str, object]
    """HAEO configuration (hub settings, participants)."""

    environment: EnvironmentInfo
    """Runtime info plus per-snapshot timestamps."""

    inputs: list[Mapping[str, object]]
    """Input sensor states used in optimization."""

    outputs: dict[str, SensorStateDict] | None
    """Output sensor states (None for historical diagnostics)."""

    missing_entity_ids: tuple[str, ...]
    """Entity IDs that were expected but not found in the recorder."""

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict for HA diagnostics output."""
        data: dict[str, object] = {
            "environment": asdict(self.environment),
            "config": self.config,
            "inputs": self.inputs,
        }
        if self.outputs is not None:
            data["outputs"] = self.outputs
        return data


def _config_from_context(context: OptimizationContext) -> dict[str, object]:
    """Build diagnostics config section from OptimizationContext.

    Uses the exact hub configuration and participant schemas the optimizer used,
    rather than re-deriving from the config entry. This captures everything:
    tiers, horizon preset, advanced settings, etc.
    """
    return {
        **dict(context.hub_config),
        "participants": dict(context.participants),
    }


def _inputs_from_context(context: OptimizationContext) -> list[Mapping[str, object]]:
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

    def _collect(value: SchemaValue | Mapping[str, object], collected: set[str]) -> None:
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


def _config_from_entry(config_entry: HaeoConfigEntry) -> dict[str, object]:
    """Build diagnostics config section from the config entry (current config).

    Used for historical diagnostics where we always use the current configuration.
    """
    participants: dict[str, object] = {}
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != ELEMENT_TYPE_NETWORK:
            raw_data = dict(subentry.data)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            raw_data.setdefault(CONF_NAME, subentry.title)
            participants[subentry.title] = raw_data

    return {
        **dict(config_entry.data),
        "participants": participants,
    }


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
) -> tuple[list[Mapping[str, object]], list[str]]:
    """Fetch input entity states from the recorder at a specific time.

    The recorder never holds the events a live run injects into calendar
    states, so each calendar's events from ``target_time`` over the longest
    horizon are fetched from the calendar and injected the same way. A calendar
    that cannot be queried is reported as missing.

    Returns:
        Tuple of (inputs, missing_entity_ids).

    """
    all_entity_ids = _collect_entity_ids_from_entry(config_entry)
    if not all_entity_ids:
        return [], []

    recorder = get_recorder_instance(hass)
    entity_id_list = sorted(all_entity_ids)

    def _query() -> dict[str, list[State]]:
        return get_significant_states_full(
            hass,
            start_time=target_time,
            end_time=target_time,
            entity_ids=entity_id_list,
            include_start_time_state=True,
            significant_changes_only=False,
            no_attributes=False,
        )

    states = await recorder.async_add_executor_job(_query)
    entity_states = {eid: slist[0] for eid, slist in states.items() if slist}

    found = [entity_states[eid] for eid in entity_id_list if eid in entity_states]
    calendars = [state.entity_id for state in found if state.entity_id.startswith(f"{CALENDAR_DOMAIN}.")]
    fetched = await asyncio.gather(
        *(
            async_fetch_calendar_events(hass, eid, target_time, target_time + HISTORICAL_CALENDAR_LOOKAHEAD)
            for eid in calendars
        )
    )
    events = dict(zip(calendars, fetched, strict=True))
    unqueryable = {eid for eid, calendar_events in events.items() if calendar_events is None}

    read_since = _meters_read_since(config_entry, entity_states, events, target_time)
    meters = sorted(read_since.keys() & entity_states.keys())
    recorded = await asyncio.gather(
        *(async_meter_totals_at(hass, eid, target_time, entity_states[eid]) for eid in meters)
    )
    totals = [
        None if meter_totals is None else totals_since(meter_totals, read_since[eid])
        for eid, meter_totals in zip(meters, recorded, strict=True)
    ]

    extra_attributes: dict[str, Mapping[str, object]] = {
        **{
            eid: {CALENDAR_EVENTS_ATTRIBUTE: found_events}
            for eid, found_events in events.items()
            if found_events is not None
        },
        **{
            eid: {METER_TOTALS_ATTRIBUTE: meter_totals}
            for eid, meter_totals in zip(meters, totals, strict=True)
            if meter_totals is not None
        },
    }
    inputs = [
        _captured_state(state, extra_attributes.get(state.entity_id))
        for state in found
        if state.entity_id not in unqueryable
    ]
    missing = (all_entity_ids - set(entity_states)) | unqueryable
    return inputs, sorted(missing)


def _meters_read_since(
    config_entry: HaeoConfigEntry,
    entity_states: Mapping[str, State],
    events: Mapping[str, list[CalendarEventDict] | None],
    target_time: datetime,
) -> dict[str, float | None]:
    """Return when each meter read by a meter input is read since, as of a past time.

    A meter input measures its meters from the window its calendars had open
    at the target time, the replayed horizon's start; a meter read by no open
    window is read since no time.
    """
    since: dict[str, float | None] = {}
    for subentry in config_entry.subentries.values():
        participant_config = {**subentry.data, CONF_ELEMENT_TYPE: subentry.subentry_type}
        if subentry.subentry_type == ELEMENT_TYPE_NETWORK or not is_element_config_schema(participant_config):
            continue
        for element_input in element_inputs(participant_config):
            meters = configured_value(participant_config, element_input.config_path)
            value = input_value(participant_config, element_input)
            if element_input.hint.meter is None or not is_entity_value(meters) or not is_entity_value(value):
                continue
            calendars = [eid for eid in value["value"] if eid not in meters["value"]]
            opened = open_window_start(
                [
                    event
                    for eid in calendars
                    if (state := entity_states.get(eid)) is not None and (found := events.get(eid)) is not None
                    for event in load_calendar_events(
                        AnnotatedState(state, {CALENDAR_EVENTS_ATTRIBUTE: found}), dt_util.get_default_time_zone()
                    )
                    or []
                ],
                target_time,
            )
            for eid in meters["value"]:
                known = since.get(eid)
                since[eid] = opened if known is None else known if opened is None else min(known, opened)
    return since


def _captured_state(state: State, extra_attributes: Mapping[str, object] | None) -> Mapping[str, object]:
    """Return a state as captured, carrying what a live run injects into it, such as calendar events."""
    captured = state.as_dict()
    if extra_attributes is None:
        return captured
    return {**captured, "attributes": {**state.attributes, **extra_attributes}}


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
        return get_significant_states_full(
            hass,
            start_time=target_time,
            end_time=target_time,
            entity_ids=[duration_entity_id, horizon_entity_id],
            include_start_time_state=True,
            significant_changes_only=False,
            no_attributes=False,
        )

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
    *,
    diagnostic_request_time: str,
    diagnostic_target_time: str | None,
    optimization_start_time: str,
    optimization_end_time: str,
    horizon_start: str,
) -> EnvironmentInfo:
    """Build the environment section of diagnostics.

    Combines static runtime facts (versions, timezone) with per-snapshot timestamps.
    """
    integration = await async_get_integration(hass, config_entry.domain)
    haeo_version = integration.version or "unknown"

    return EnvironmentInfo(
        diagnostics_version=DIAGNOSTICS_SCHEMA_VERSION,
        ha_version=ha_version,
        haeo_version=haeo_version,
        timezone=str(dt_util.get_default_time_zone()),
        diagnostic_request_time=diagnostic_request_time,
        diagnostic_target_time=diagnostic_target_time,
        optimization_start_time=optimization_start_time,
        optimization_end_time=optimization_end_time,
        horizon_start=horizon_start,
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
    if target_time is None:
        runtime_data = config_entry.runtime_data
        if (
            not isinstance(runtime_data, HaeoRuntimeData)
            or not runtime_data.coordinator
            or not runtime_data.coordinator.data
        ):
            msg = "Cannot collect diagnostics: no optimization has completed yet"
            raise RuntimeError(msg)

        coordinator_data = runtime_data.coordinator.data
        return await diagnostics_from_context(
            hass,
            config_entry,
            coordinator_data.context,
            started_at=coordinator_data.started_at,
            completed_at=coordinator_data.completed_at,
            outputs=get_output_sensors(hass, config_entry),
        )

    run = await _get_last_run_before(hass, config_entry, target_time)
    if run is None:
        msg = "Cannot collect diagnostics: no optimization run found before the requested time"
        raise RuntimeError(msg)

    started_at, completed_at, horizon_start = run
    config = _config_from_entry(config_entry)
    config["version"] = config_entry.version
    config["minor_version"] = config_entry.minor_version
    inputs, missing = await _fetch_inputs_at(hass, config_entry, started_at)
    environment = await _build_environment(
        hass,
        config_entry,
        diagnostic_request_time=_to_local_iso(dt_util.utcnow()),
        diagnostic_target_time=_to_local_iso(target_time),
        optimization_start_time=_to_local_iso(started_at),
        optimization_end_time=_to_local_iso(completed_at),
        horizon_start=horizon_start,
    )

    return DiagnosticsResult(
        config=async_redact_data(config, _REDACTED_CONFIG_KEYS),
        environment=environment,
        inputs=inputs,
        outputs=None,
        missing_entity_ids=tuple(missing),
    )


async def diagnostics_from_context(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    context: OptimizationContext,
    *,
    started_at: datetime,
    completed_at: datetime,
    outputs: dict[str, SensorStateDict] | None,
) -> DiagnosticsResult:
    """Collect diagnostics from the config and inputs an optimization used.

    An optimization that failed has no outputs, but its context still holds
    everything needed to run it again.
    """
    config = _config_from_context(context)
    config["version"] = config_entry.version
    config["minor_version"] = config_entry.minor_version
    environment = await _build_environment(
        hass,
        config_entry,
        diagnostic_request_time=_to_local_iso(dt_util.utcnow()),
        diagnostic_target_time=None,
        optimization_start_time=_to_local_iso(started_at),
        optimization_end_time=_to_local_iso(completed_at),
        horizon_start=_to_local_iso(context.horizon_start),
    )
    return DiagnosticsResult(
        config=async_redact_data(config, _REDACTED_CONFIG_KEYS),
        environment=environment,
        inputs=_inputs_from_context(context),
        outputs=outputs,
        missing_entity_ids=(),
    )


__all__ = [
    "DIAGNOSTICS_SCHEMA_VERSION",
    "DiagnosticsResult",
    "EnvironmentInfo",
    "collect_diagnostics",
    "diagnostics_from_context",
]
