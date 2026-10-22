"""Data update coordinator for the Home Assistant Energy Optimizer integration."""

import asyncio
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import time
from typing import TYPE_CHECKING, Literal, TypedDict

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import STATE_ON, EntityCategory, UnitOfTime
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import EventStateChangedData, async_call_later, async_track_state_change_event
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonValueType

from custom_components.haeo.const import (
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_PENDING,
    OPTIMIZATION_STATUS_SUCCESS,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    NetworkOutputName,
)
from custom_components.haeo.core.adapters.network_builder import ElementUpdater, build_network, periods_in_hours
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_RELAX_INFEASIBLE,
    DEFAULT_DEBOUNCE_SECONDS,
)
from custom_components.haeo.core.context import OptimizationContext
from custom_components.haeo.core.data.loader.config_loader import load_element_config_from_values
from custom_components.haeo.core.data.loader.extractors.haeo import InterpolationMode
from custom_components.haeo.core.model import ModelOutputName, Network, OutputData, OutputType, SolverError
from custom_components.haeo.core.model.infeasibility import InfeasibleError, RowLabel, listing
from custom_components.haeo.core.model.topology import serialize_topology
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import currency_symbol, localize_currency, price_currency
from custom_components.haeo.elements import (
    ElementDeviceName,
    ElementOutputName,
    collect_element_subentries,
    get_element_configs,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.input_stores import (
    raise_for_rejected_input,
    unavailable_input_placeholders,
    unavailable_input_sources,
)
from custom_components.haeo.repairs import (
    create_optimization_infeasible_issue,
    create_optimization_persistent_failure_issue,
    create_optimization_relaxed_issue,
    dismiss_optimization_failure_issue,
    optimization_infeasible_issue_raised,
    optimization_relaxed_issue_raised,
    sync_mixed_price_currencies_issue,
    sync_unavailable_input_issues,
)
from custom_components.haeo.services import async_save_diagnostics

from .network import evaluate_network_connectivity

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
    from custom_components.haeo.core.data.input_store import InputStore, InputValue
    from custom_components.haeo.elements import InputFieldPath
    from custom_components.haeo.input_stores import InputStoreKey

_LOGGER = logging.getLogger(__name__)

# How long optimizations must keep failing before HAEO raises a repair issue, so a
# brief failure, such as an input that is unavailable for a moment, does not raise one
FAILURE_SECONDS_BEFORE_REPAIR_ISSUE = 300


class ReportedUpdateFailed(UpdateFailed):
    """An optimization failure that raises a repair issue of its own.

    The general optimization failure issue is not raised for it, so the user
    sees one issue that names the cause rather than two.
    """


class ForecastPoint(TypedDict):
    """Single point in a forecast time series.

    Attributes:
        time: Timestamp as datetime object (timezone-aware)
        value: Forecast value (numeric or other types depending on output type)

    """

    time: datetime
    value: float | str


@dataclass(frozen=True, slots=True)
class CoordinatorOutput:
    """Processed output ready for Home Assistant entities."""

    type: OutputType
    unit: str | None
    state: StateType | None
    forecast: list[ForecastPoint] | None
    # How the forecast varies between its points, when it is not linear
    interpolation_mode: InterpolationMode | None = None
    direction: Literal["+", "-"] | None = None
    entity_category: EntityCategory | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    options: tuple[str, ...] | None = None
    advanced: bool = False
    priority: int | None = None
    fixed: bool = False
    display_precision: int | None = None


DEVICE_CLASS_MAP: dict[OutputType, SensorDeviceClass] = {
    OutputType.POWER: SensorDeviceClass.POWER,
    OutputType.POWER_FLOW: SensorDeviceClass.POWER,
    OutputType.POWER_LIMIT: SensorDeviceClass.POWER,
    OutputType.ENERGY: SensorDeviceClass.ENERGY,
    OutputType.STATE_OF_CHARGE: SensorDeviceClass.BATTERY,
    OutputType.COST: SensorDeviceClass.MONETARY,
    OutputType.PRICE: SensorDeviceClass.MONETARY,
    OutputType.SHADOW_PRICE: SensorDeviceClass.MONETARY,
    OutputType.DURATION: SensorDeviceClass.DURATION,
    OutputType.STATUS: SensorDeviceClass.ENUM,
}

STATE_CLASS_MAP: dict[OutputType, SensorStateClass | None] = {
    OutputType.POWER: SensorStateClass.MEASUREMENT,
    OutputType.POWER_FLOW: SensorStateClass.MEASUREMENT,
    OutputType.POWER_LIMIT: SensorStateClass.MEASUREMENT,
    OutputType.STATE_OF_CHARGE: SensorStateClass.MEASUREMENT,
    OutputType.DURATION: SensorStateClass.MEASUREMENT,
}

STATUS_OPTIONS: tuple[str, ...] = tuple(
    sorted(  # Keep a stable order for enum options in Home Assistant UI
        {
            OPTIMIZATION_STATUS_FAILED,
            OPTIMIZATION_STATUS_PENDING,
            OPTIMIZATION_STATUS_SUCCESS,
        }
    )
)


def detect_currency_symbol(
    source_states: Mapping[str, "EntityState"],
    *,
    fallback_currency: str | None = None,
) -> str:
    """Detect the user's currency symbol from source entity units.

    Scans entity states for a price-like unit (e.g. ``£/kWh``) and returns the
    currency prefix, or the main currency of a minor unit such as ``p/kWh``.
    Cents written as ``c/kWh`` name no currency and are skipped. Falls back to
    the configured currency when no price entity names one, and then ``$`` if
    no configured currency is available. A currency code such as ``EUR`` reads
    as its symbol, so every spelling of a currency shows the same way.
    """
    for state in source_states.values():
        if (currency := price_currency(state.attributes.get("unit_of_measurement"))) is not None:
            return currency_symbol(currency)
    return currency_symbol(fallback_currency) if fallback_currency else "$"


def price_currency_sources(source_states: Mapping[str, "EntityState"]) -> dict[str, list[str]]:
    """Group the source entities that report a price by the currency they report it in.

    A currency code and its symbol, such as ``EUR`` and ``€``, group together.
    Cents written as ``c/kWh`` name no currency and are left out.
    """
    sources: dict[str, list[str]] = {}
    for entity_id, state in source_states.items():
        if (currency := price_currency(state.attributes.get("unit_of_measurement"))) is not None:
            sources.setdefault(currency_symbol(currency), []).append(entity_id)
    return sources


def forecast_datetimes(timestamps: Sequence[float]) -> tuple[datetime, ...] | None:
    """Convert horizon timestamps to datetimes in Home Assistant's time zone.

    Every output sensor's forecast shares these times, so they are converted once
    per optimization. Returns None when a timestamp is outside the supported range.
    """
    local_tz = dt_util.get_default_time_zone()
    try:
        return tuple(datetime.fromtimestamp(timestamp, tz=local_tz) for timestamp in timestamps)
    except ValueError:
        return None


def build_coordinator_output(
    output_name: ElementOutputName,
    output_data: OutputData,
    *,
    forecast_times: tuple[datetime, ...] | None,
    currency_sym: str,
) -> CoordinatorOutput:
    """Convert model output values into coordinator state and forecast.

    This function handles the boundary alignment problem where different output types
    require different numbers of timestamps:

    - **Interval values** (power, prices): Average values over time periods.
      These have n values, each representing the average from the start
      of that period to its end. Use the first n timestamps.

    - **Boundary values** (energy, SOC): Instantaneous state at specific points in time.
      These have n+1 values representing the state at each time boundary.
      Use all n+1 timestamps.

    The forecast_times tuple contains n+1 datetimes (all boundaries), from
    ``forecast_datetimes``. Each output type zips its values with however
    many times it needs.

    Example with 3 periods of 5 minutes starting at 12:00:
      - forecast_times: [12:00, 12:05, 12:10, 12:15] (n+1 = 4 boundaries)
      - Interval values (n=3): zip with [12:00, 12:05, 12:10]
      - Boundary values (n=4): zip with [12:00, 12:05, 12:10, 12:15]

    Interval forecasts carry the previous interpolation mode, so a HAEO input
    reading one holds each value across its period rather than ramping.
    """

    values = tuple(output_data.values)
    if output_data.state is not None:
        state = output_data.state
    elif not values:
        state = None
    elif output_data.state_last:
        state = values[-1]
    else:
        state = values[0]
    forecast: list[ForecastPoint] | None = None
    interpolation_mode: InterpolationMode | None = None

    if forecast_times and len(values) > 1:
        # Interval values use n_periods times and boundary values use all n_periods+1
        if len(values) not in (len(forecast_times) - 1, len(forecast_times)):
            msg = (
                f"Output {output_name!r} has {len(values)} values for {len(forecast_times)} forecast times; "
                f"expected {len(forecast_times) - 1} interval values or {len(forecast_times)} boundary values"
            )
            raise ValueError(msg)
        forecast = [
            ForecastPoint(time=time, value=value)
            for time, value in zip(forecast_times[: len(values)], values, strict=True)
        ]
        if len(values) < len(forecast_times):
            interpolation_mode = InterpolationMode.PREVIOUS

    return CoordinatorOutput(
        type=output_data.type,
        unit=localize_currency(output_data.unit, currency_sym),
        state=state,
        forecast=forecast,
        interpolation_mode=interpolation_mode,
        direction=output_data.direction,
        entity_category=EntityCategory.DIAGNOSTIC if output_data.diagnostic else None,
        device_class=DEVICE_CLASS_MAP.get(output_data.type),
        state_class=STATE_CLASS_MAP.get(output_data.type),
        options=(STATUS_OPTIONS if output_data.type == OutputType.STATUS else None),
        advanced=output_data.advanced,
        priority=output_data.priority,
        fixed=output_data.fixed,
        display_precision=output_data.display_precision,
    )


def build_optimization_context(
    hub_config: Mapping[str, object],
    participant_configs: Mapping[str, ElementConfigSchema],
    input_stores: Mapping["InputStoreKey", "InputStore"],
    horizon_manager: HorizonManager,
) -> OptimizationContext:
    """Build an optimization context by pulling from existing sources."""
    source_states: dict[str, EntityState] = {}
    for store in input_stores.values():
        source_states.update(store.captured_source_states)

    horizon_start = horizon_manager.current_start_time
    if horizon_start is None:
        horizon_start = datetime.now(UTC)

    return OptimizationContext(
        hub_config=hub_config,
        horizon_start=horizon_start,
        participants=dict(participant_configs),
        source_states=source_states,
    )


type SubentryDevices = dict[ElementDeviceName, dict[ElementOutputName | NetworkOutputName, CoordinatorOutput]]


@dataclass(slots=True)
class CoordinatorData:
    """Result of an optimization run including inputs and outputs."""

    context: OptimizationContext
    """Immutable snapshot of all inputs used for this optimization."""

    outputs: dict[str, SubentryDevices]
    """Element outputs organized by element_name -> device_name -> output_name."""

    started_at: datetime
    """When the optimization started."""

    completed_at: datetime
    """When the optimization completed."""


class HaeoDataUpdateCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Data update coordinator for HAEO integration.

    Reads pre-loaded data from input entities (HaeoInputNumber/HaeoInputSwitch)
    instead of loading directly from source entities. This provides:
    - Single source of truth for loaded data
    - User visibility into intermediate values
    - Event-driven optimization triggered by input entity changes

    Custom debouncing logic:
    - Optimize immediately when inputs are valid and aligned
    - During cooldown period, batch updates and optimize after cooldown expires
    - No time-based updates - driven entirely by input entity changes
    """

    config_entry: "HaeoConfigEntry"

    def __init__(self, hass: HomeAssistant, config_entry: "HaeoConfigEntry") -> None:
        """Initialize the coordinator for an entry whose runtime data is already set.

        Raises:
            RuntimeError: When the entry has no runtime data.

        """
        if config_entry.runtime_data is None:
            msg = "The config entry's runtime data must be set before its coordinator is created"
            raise RuntimeError(msg)
        self._runtime_data: HaeoRuntimeData = config_entry.runtime_data

        # Built by async_initialize, once every input has loaded
        self._network: Network | None = None
        self._element_updaters: dict[str, ElementUpdater] = {}
        # The network's outputs are keyed by its subentry's title, which its sensors look them up by
        self._network_subentry_title = next(
            subentry.title
            for subentry in config_entry.subentries.values()
            if subentry.subentry_type == ELEMENT_TYPE_NETWORK
        )
        self.topology: dict[str, JsonValueType] = {}  # Serialized topology for frontend

        # Snapshot the participant structure (which elements exist and the shape
        # of each, including list fields like policy rules) taken from the same
        # subentry view that built the input stores. Field *values* are read live
        # from the stores at optimization time, so value edits still apply; only
        # the structure is fixed. Structural changes always trigger a reload,
        # which rebuilds both the stores and this snapshot together. Reading the
        # structure live instead would let a subentry committed during setup's
        # awaits (which schedules its own reload) leak in without matching
        # stores, breaking config assembly.
        self._participant_configs: dict[str, ElementConfigSchema] = get_element_configs(
            config_entry,
            {
                participant.name: participant.subentry.subentry_id
                for participant in collect_element_subentries(config_entry)
            },
        )

        # Custom debouncing state
        advanced_data = config_entry.data.get(HUB_SECTION_ADVANCED, {})
        self._debounce_seconds = float(advanced_data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS))
        self._relax_infeasible: bool = advanced_data.get(CONF_RELAX_INFEASIBLE, False)
        self._last_optimization_time: float | None = None
        self._debounce_timer: CALLBACK_TYPE | None = None
        # Held while an optimization runs, so optimizations never overlap
        self._optimization_lock = asyncio.Lock()
        # Whether an optimization was requested that no optimization has started reading inputs for since
        self._rerun_wanted: bool = False
        # When optimizations started failing, and whether that failure raises an issue of its own
        self._failing_since: float | None = None
        self._failure_reported = False
        self._failure_issue_raised = False
        # Elements whose inputs changed since an optimization last applied them to the network
        self._stale_elements: set[str] = set()

        # No update_interval - we're event-driven from input entities
        # No request_refresh_debouncer - we handle debouncing ourselves
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            config_entry=config_entry,
            always_update=False,
        )

        # State change subscriptions - set up in async_initialize()
        self._state_change_unsubs: list[Callable[[], None]] = []

    @property
    def network(self) -> Network:
        """Return the network that async_initialize built.

        Raises:
            RuntimeError: Before async_initialize has built it.

        """
        if self._network is None:
            msg = "The network is built by async_initialize"
            raise RuntimeError(msg)
        return self._network

    async def async_initialize(self) -> None:
        """Initialize the network and set up subscriptions.

        Must be called after the coordinator is created but before any optimizations.
        This is called from async_setup_entry after all input entities are loaded.
        """
        loaded_configs = self._load_from_input_stores()

        _LOGGER.debug("Initializing network with %d participants", len(loaded_configs))

        self._network, self._element_updaters = build_network(
            f"haeo_network_{self.config_entry.entry_id}",
            loaded_configs,
            self._runtime_data.horizon_manager.periods_seconds,
            relax_infeasible=self._relax_infeasible,
        )

        # Build topology for frontend card
        element_types = {name: str(config[CONF_ELEMENT_TYPE]) for name, config in loaded_configs.items()}
        self.topology = serialize_topology(self._network, element_types=element_types)
        evaluate_network_connectivity(self.hass, self.config_entry, participants=loaded_configs)

        self._subscribe_to_input_stores()

    def _subscribe_to_input_stores(self) -> None:
        """Subscribe to value changes from input stores.

        Sets up per-store listeners so each store only updates its specific
        element's TrackedParams when its value changes.

        Also subscribes to the auto-optimize switch to control horizon manager
        pause/resume and trigger optimization on re-enable.
        """
        runtime_data = self._runtime_data

        # Subscribe to auto-optimize switch state changes
        if runtime_data.auto_optimize_switch is not None:
            self._state_change_unsubs.append(
                async_track_state_change_event(
                    self.hass,
                    [runtime_data.auto_optimize_switch.entity_id],
                    self._handle_auto_optimize_switch_change,
                )
            )
            # Apply the switch's initial state, which may have been restored. This
            # happens before subscribing to the horizon, so resuming it does not
            # request the optimization that setup runs itself.
            self._apply_auto_optimize_state(is_enabled=runtime_data.auto_optimize_switch.is_on or False)

        # Horizon changes require a full re-optimization. The new period durations
        # are applied to the network when that optimization runs.
        runtime_data.horizon_manager.subscribe(self.signal_optimization_stale)

        # Subscribe each store to update only its element when its value changes
        for (element_name, _field_path), store in runtime_data.input_stores.items():
            self._state_change_unsubs.append(store.add_listener(self._create_store_listener(element_name)))

    def _create_store_listener(self, element_name: str) -> Callable[[], None]:
        """Create a listener that updates a specific element when its inputs change."""

        @callback
        def store_listener() -> None:
            self._handle_element_update(element_name)

        return store_listener

    @callback
    def _handle_element_update(self, element_name: str) -> None:
        """Mark an element whose inputs changed, so the next optimization applies them, and request one."""
        self._stale_elements.add(element_name)
        self.signal_optimization_stale()

    @callback
    def _handle_auto_optimize_switch_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle auto-optimize switch state change.

        Turning it on resumes the horizon, whose notification requests an
        optimization that catches up on changes made while it was off.
        Turning it off pauses the horizon.
        """
        new_state = event.data["new_state"]
        if new_state is None:
            return

        self._apply_auto_optimize_state(is_enabled=new_state.state == STATE_ON)

    def _apply_auto_optimize_state(self, *, is_enabled: bool) -> None:
        """Pause or resume the horizon manager to match the auto-optimize setting."""
        if is_enabled:
            self._runtime_data.horizon_manager.resume()
        else:
            self._cancel_debounce_timer()
            self._runtime_data.horizon_manager.pause()

    @property
    def auto_optimize_enabled(self) -> bool:
        """Return whether automatic optimization is enabled.

        Reads from the auto-optimize switch entity stored in runtime_data.
        """
        switch = self._runtime_data.auto_optimize_switch
        if switch is None:
            msg = "auto_optimize_switch not available"
            raise RuntimeError(msg)
        return switch.is_on or False

    async def async_run_optimization(self) -> None:
        """Optimize now, bypassing debouncing and the auto-optimize setting.

        Raises:
            HomeAssistantError: While forecast inputs are still loading for a new horizon.

        """
        if not await self._optimize():
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="inputs_not_aligned")

    async def async_refresh(self) -> None:
        """Optimize with the current inputs, after any optimization already running."""
        await self._optimize()

    async def async_request_refresh(self) -> None:
        """Optimize when the debounce window allows, as an entity update requests."""
        self._request_optimization()

    async def _optimize(self) -> bool:
        """Optimize with the current inputs once any optimization already running ends.

        Returns False when the optimization is skipped because forecast inputs are
        still loading for a new horizon; they request another once loaded. Requests
        made while an optimization runs share one follow-up, since it reads every
        input as it is when it starts.
        """
        self._rerun_wanted = True
        async with self._optimization_lock:
            # An optimization that started after this request has already read the inputs
            if not self._rerun_wanted:
                return True
            if not self._are_inputs_aligned():
                return False
            self._rerun_wanted = False
            await super().async_refresh()
        # Inputs that changed while it ran request another through the debounce window
        if self._rerun_wanted:
            self.signal_optimization_stale()
        return True

    @callback
    def signal_optimization_stale(self) -> None:
        """Request an optimization because inputs changed, when auto-optimize is on."""
        if self.auto_optimize_enabled:
            self._request_optimization()

    @callback
    def _request_optimization(self) -> None:
        """Optimize now, or once the running optimization and the debounce window have passed."""
        self._rerun_wanted = True
        # The running optimization requests the follow-up when it ends
        if self._optimization_lock.locked() or self._debounce_timer is not None:
            return
        elapsed = time.time() - (self._last_optimization_time or 0.0)
        if elapsed < self._debounce_seconds:
            self._debounce_timer = async_call_later(
                self.hass, self._debounce_seconds - elapsed, self._debounce_timer_callback
            )
            return
        self.hass.async_create_task(self._optimize())

    @callback
    def _debounce_timer_callback(self, _now: datetime) -> None:
        """Optimize once the debounce window has passed, unless an optimization has met the request since."""
        self._debounce_timer = None
        if self._rerun_wanted:
            self.hass.async_create_task(self._optimize())

    def _cancel_debounce_timer(self) -> None:
        """Cancel the optimization waiting out the debounce window, if one is."""
        if self._debounce_timer is not None:
            self._debounce_timer()
            self._debounce_timer = None

    def _are_inputs_aligned(self) -> bool:
        """Return whether every forecast input is loaded for the horizon's current start.

        Scalar (non-forecast) inputs are alignment-neutral since they have no
        time-series data to align.
        """
        expected_start = self._runtime_data.horizon_manager.get_forecast_timestamps()[0]
        # A store that rejected its source's value, or could not load it, keeps its
        # previous horizon; the update reports the problem instead of waiting on
        # alignment that will not come.
        return all(
            store.horizon_start is not None and abs(store.horizon_start - expected_start) <= 1.0
            for store in self._runtime_data.input_stores.values()
            if store.time_series and store.available
        )

    def _load_from_input_stores(self) -> dict[str, ElementConfigData]:
        """Assemble every element's config from the resolved values of its input stores."""
        forecast_times = self._runtime_data.horizon_manager.get_forecast_timestamps()
        field_values: dict[str, dict[InputFieldPath, InputValue | None]] = {}
        for (name, field_path), store in self._runtime_data.input_stores.items():
            field_values.setdefault(name, {})[field_path] = store.value
        return {
            name: load_element_config_from_values(name, config, field_values.get(name, {}), forecast_times)
            for name, config in self._participant_configs.items()
        }

    def cleanup(self) -> None:
        """Clean up coordinator resources when unloading."""
        for unsub in self._state_change_unsubs:
            unsub()
        self._state_change_unsubs.clear()
        self._cancel_debounce_timer()
        self._stale_elements.clear()

    async def _save_failure_diagnostics(
        self, context: OptimizationContext, started_at: datetime, kind: str, failure: dict[str, object]
    ) -> str | None:
        """Save diagnostics of the optimization that just failed or was relaxed, and return the file's path.

        They hold the config and inputs the optimization used, so the failure can be
        run again from the file a user attaches to a report. Returns None when the
        diagnostics cannot be collected or written, so its issue waits for the next
        optimization rather than the plan or its error being lost.
        """
        # Imported here because the diagnostics package imports the integration, which imports this module
        from custom_components.haeo.diagnostics import diagnostics_from_context  # noqa: PLC0415

        now = dt_util.now()
        try:
            result = await diagnostics_from_context(
                self.hass, self.config_entry, context, started_at=started_at, completed_at=now, outputs=None
            )
            path = await async_save_diagnostics(self.hass, {**result.to_dict(), "failure": failure}, kind, now)
        except Exception:
            # Any failure here must not replace the report of the plan it describes
            _LOGGER.exception(
                "Could not save the %s plan's diagnostics, so its repair issue waits for the next plan", kind
            )
            return None
        return str(path)

    @property
    def optimization_status(self) -> str:
        """Return whether the latest optimization succeeded, failed, or has not run yet."""
        if not self.last_update_success:
            return OPTIMIZATION_STATUS_FAILED
        return OPTIMIZATION_STATUS_SUCCESS if self.data else OPTIMIZATION_STATUS_PENDING

    @property
    def optimization_error(self) -> str | None:
        """Return why the latest optimization failed, or None if it did not fail."""
        error = self.last_exception
        if self.last_update_success or error is None:
            return None
        message = str(error)
        if isinstance(error, HomeAssistantError):
            return message or type(error).__name__
        # Other exceptions often need their type to make sense, such as a KeyError
        return f"{type(error).__name__}: {message}" if message else type(error).__name__

    @callback
    def _async_refresh_finished(self) -> None:
        """Report failed optimizations.

        Home Assistant only notifies listeners when a refresh switches between
        failing and succeeding, so a failure that follows another failure notifies
        them here, keeping the reported error current. Once optimizations have kept
        failing for a while, a repair issue is raised, and the next success
        dismisses it.
        """
        super()._async_refresh_finished()
        if self.last_update_success:
            self._failing_since = None
            self._failure_issue_raised = False
            dismiss_optimization_failure_issue(self.hass, self.config_entry.entry_id)
            return
        now = time.time()
        reported = isinstance(self.last_exception, ReportedUpdateFailed)
        if self._failing_since is None:
            self._failing_since = now
            self._failure_reported = reported
            return
        self.async_update_listeners()
        # Time spent failing for a cause with its own issue does not count toward the general one
        if reported != self._failure_reported:
            self._failing_since = now
            self._failure_reported = reported
            # A cause with its own issue replaces the general one, so the user sees one issue
            self._failure_issue_raised = False
            dismiss_optimization_failure_issue(self.hass, self.config_entry.entry_id)
        if reported:
            return
        if not self._failure_issue_raised and now - self._failing_since >= FAILURE_SECONDS_BEFORE_REPAIR_ISSUE:
            self._failure_issue_raised = True
            create_optimization_persistent_failure_issue(
                self.hass, self.config_entry.entry_id, str(self.optimization_error)
            )

    async def _async_update_data(self) -> CoordinatorData:
        """Optimize with the inputs as they are now and build the outputs of the plan."""
        start_time = time.time()
        started_at = dt_util.utc_from_timestamp(start_time).astimezone()
        # Mark the start at once, so the debounce window holds back requests while this runs
        self._last_optimization_time = start_time

        horizon_manager = self._runtime_data.horizon_manager
        forecast_timestamps = horizon_manager.get_forecast_timestamps()
        context = build_optimization_context(
            hub_config=self.config_entry.data,
            participant_configs=self._participant_configs,
            input_stores=self._runtime_data.input_stores,
            horizon_manager=horizon_manager,
        )
        self._check_inputs(context)
        loaded_configs = self._load_from_input_stores()

        _LOGGER.debug("Running optimization with %d participants", len(loaded_configs))

        # Bring the network to the horizon the inputs were loaded for, and apply the
        # inputs that changed, before the solve is handed to the executor, so the
        # network is never mutated while it is being solved
        network = self.network
        network.update_periods(periods_in_hours(horizon_manager.periods_seconds))
        for element_name in self._stale_elements:
            self._element_updaters[element_name](loaded_configs[element_name])
        self._stale_elements.clear()

        cost = await self._solve(network, context, started_at, forecast_timestamps)

        end_time = time.time()
        self._last_optimization_time = end_time
        _LOGGER.debug("Optimization completed successfully with cost: %s", cost)
        await self._report_relaxations(network, context, started_at, forecast_timestamps)

        return CoordinatorData(
            context=context,
            outputs=self._build_outputs(
                network, context, loaded_configs, cost, end_time - start_time, forecast_timestamps
            ),
            started_at=started_at,
            completed_at=dt_util.utc_from_timestamp(end_time).astimezone(),
        )

    def _check_inputs(self, context: OptimizationContext) -> None:
        """Raise when an input cannot be read, and keep the input repair issues current.

        When any input is unavailable the optimization is skipped, matching the
        behaviour during initial setup where the integration stays in the "not
        ready" state until every store can supply data. Inputs that have no reading
        get a repair issue naming their sensors; rejected values are reported
        through their own error.
        """
        input_stores = self._runtime_data.input_stores
        entry_id = self.config_entry.entry_id
        unavailable = unavailable_input_sources(input_stores, lambda store: not store.available)
        sync_unavailable_input_issues(self.hass, entry_id, unavailable)
        raise_for_rejected_input(input_stores, UpdateFailed)
        if unavailable:
            key, entities = next(iter(unavailable.items()))
            raise ReportedUpdateFailed(
                translation_domain=DOMAIN,
                translation_key="input_unavailable",
                translation_placeholders=unavailable_input_placeholders(key, entities),
            )
        sync_mixed_price_currencies_issue(self.hass, entry_id, price_currency_sources(context.source_states))

    async def _solve(
        self,
        network: Network,
        context: OptimizationContext,
        started_at: datetime,
        forecast_timestamps: Sequence[float],
    ) -> float:
        """Solve the network in the executor, reporting a plan that cannot be found."""
        entry_id = self.config_entry.entry_id
        try:
            return await self.hass.async_add_executor_job(network.optimize)
        except InfeasibleError as error:
            translation_key = "optimization_infeasible_unexplained"
            placeholders: dict[str, str] = {}
            if error.conflicts:
                translation_key = "optimization_infeasible"
                placeholders = {
                    "elements": _element_names(error.conflicts, context.participants),
                    "minutes": _minutes_into_plan(error.conflicts, forecast_timestamps),
                }
            if not optimization_infeasible_issue_raised(self.hass, entry_id) and (
                diagnostics := await self._save_failure_diagnostics(
                    context,
                    started_at,
                    "infeasible",
                    {"conflicts": [str(row) for row in error.conflicts]},
                )
            ):
                create_optimization_infeasible_issue(
                    self.hass,
                    entry_id,
                    translation_key,
                    {**placeholders, "planned_at": _plan_start(forecast_timestamps)},
                    diagnostics,
                )
            # Without its diagnostics the issue is not raised, so the general one reports the failure
            failure = (
                ReportedUpdateFailed if optimization_infeasible_issue_raised(self.hass, entry_id) else UpdateFailed
            )
            raise failure(
                translation_domain=DOMAIN,
                translation_key=translation_key,
                translation_placeholders=placeholders,
            ) from error
        except SolverError as error:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="optimization_solver_failed",
                translation_placeholders={"status": error.status},
            ) from error

    async def _report_relaxations(
        self,
        network: Network,
        context: OptimizationContext,
        started_at: datetime,
        forecast_timestamps: Sequence[float],
    ) -> None:
        """Log a plan that relaxed constraints, and raise its repair issue unless one is already raised."""
        if not network.relaxations:
            return
        _LOGGER.warning("The plan relaxed constraints it cannot meet: %s", listing(map(str, network.relaxations)))
        entry_id = self.config_entry.entry_id
        if optimization_relaxed_issue_raised(self.hass, entry_id):
            return
        diagnostics = await self._save_failure_diagnostics(
            context,
            started_at,
            "relaxed",
            {
                "conflicts": [str(row) for row in network.conflicts],
                "relaxations": [str(relaxation) for relaxation in network.relaxations],
            },
        )
        if diagnostics is None:
            return
        relaxed_rows = [relaxation.row for relaxation in network.relaxations]
        conflicts = network.conflicts or relaxed_rows
        create_optimization_relaxed_issue(
            self.hass,
            entry_id,
            {
                "elements": _element_names(conflicts, context.participants),
                "minutes": _minutes_into_plan(conflicts, forecast_timestamps),
                "relaxed_elements": _element_names(relaxed_rows, context.participants),
                "relaxed_periods": str(len({row.period for row in relaxed_rows if row.period is not None})),
                "planned_at": _plan_start(forecast_timestamps),
            },
            diagnostics,
        )

    def _build_outputs(
        self,
        network: Network,
        context: OptimizationContext,
        loaded_configs: Mapping[str, ElementConfigData],
        cost: float,
        duration: float,
        forecast_timestamps: Sequence[float],
    ) -> dict[str, SubentryDevices]:
        """Build the outputs of a plan, keyed by element, device, and output name."""
        currency_sym = detect_currency_symbol(context.source_states, fallback_currency=self.hass.config.currency)
        network_output_data: dict[NetworkOutputName, OutputData] = {
            OUTPUT_NAME_OPTIMIZATION_COST: OutputData(type=OutputType.COST, unit="$", values=(cost,)),
            OUTPUT_NAME_OPTIMIZATION_DURATION: OutputData(
                type=OutputType.DURATION, unit=UnitOfTime.SECONDS, values=(duration,), diagnostic=True
            ),
        }
        outputs: dict[str, SubentryDevices] = {
            # HAEO outputs use network subentry name as key, network element type as device
            self._network_subentry_title: {
                ELEMENT_TYPE_NETWORK: {
                    name: build_coordinator_output(name, output, forecast_times=None, currency_sym=currency_sym)
                    for name, output in network_output_data.items()
                }
            }
        }

        model_outputs: dict[str, Mapping[ModelOutputName, OutputData]] = {
            element_name: element.outputs() for element_name, element in network.elements.items()
        }
        forecast_times = forecast_datetimes(forecast_timestamps)

        # Each element's adapter turns model outputs into the outputs of its devices,
        # of which an element may have several (e.g., battery regions)
        for element_name, element_config in context.participants.items():
            element_type = element_config[CONF_ELEMENT_TYPE]
            try:
                adapter_outputs: Mapping[ElementDeviceName, Mapping[ElementOutputName, OutputData]] = ELEMENT_TYPES[
                    element_type
                ].outputs(
                    name=element_name,
                    model_outputs=model_outputs,
                    config=loaded_configs[element_name],
                    periods=network.periods,
                )
            except KeyError:
                _LOGGER.exception(
                    "Failed to get outputs for config element %r (type=%r): missing model element. "
                    "Available model elements: %s",
                    element_name,
                    element_type,
                    list(model_outputs.keys()),
                )
                raise

            subentry_devices: SubentryDevices = {
                device_name: {
                    output_name: build_coordinator_output(
                        output_name, output_data, forecast_times=forecast_times, currency_sym=currency_sym
                    )
                    for output_name, output_data in device_outputs.items()
                }
                for device_name, device_outputs in adapter_outputs.items()
                if device_outputs
            }
            if subentry_devices:
                outputs[element_name] = subentry_devices
        return outputs


def _participant_name(model_element: str, participants: Collection[str]) -> str:
    """Return the configured element a model element belongs to, such as ``Grid`` for ``Grid:import``."""
    owners = [name for name in participants if model_element == name or model_element.startswith(f"{name}:")]
    return max(owners, key=len, default=model_element)


def _plan_start(forecast_timestamps: Sequence[float]) -> str:
    """Return the local time the plan starts, which places a repair issue read later."""
    return f"{dt_util.as_local(dt_util.utc_from_timestamp(forecast_timestamps[0])):%Y-%m-%d %H:%M}"


def _element_names(rows: Sequence[RowLabel], participants: Collection[str]) -> str:
    """Return the configured elements some constraint rows belong to, in the order they first appear."""
    return ", ".join(dict.fromkeys(_participant_name(row.element, participants) for row in rows))


def _minutes_into_plan(rows: Sequence[RowLabel], forecast_timestamps: Sequence[float]) -> str:
    """Return the whole minutes from the start of the plan to the first period any of the rows applies in.

    A person can find that point in the plan without reading timestamps.
    """
    periods = [row.period for row in rows if row.period is not None]
    first = forecast_timestamps[min(periods)] if periods else forecast_timestamps[0]
    return str(round((first - forecast_timestamps[0]) / 60))


__all__ = [
    "STATUS_OPTIONS",
    "CoordinatorData",
    "CoordinatorOutput",
    "ForecastPoint",
    "HaeoDataUpdateCoordinator",
    "OptimizationContext",
    "build_coordinator_output",
    "build_optimization_context",
    "forecast_datetimes",
]
