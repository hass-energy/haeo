"""Data update coordinator for the Home Assistant Energy Optimizer integration."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import time
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, EntityCategory, UnitOfTime
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import EventStateChangedData, async_call_later, async_track_state_change_event
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import numpy as np

from custom_components.haeo.const import (
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_PENDING,
    OPTIMIZATION_STATUS_SUCCESS,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    NetworkOutputName,
)
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import CONF_DEBOUNCE_SECONDS, CONF_ELEMENT_TYPE, DEFAULT_DEBOUNCE_SECONDS
from custom_components.haeo.core.context import OptimizationContext
from custom_components.haeo.core.data.loader.config_loader import load_element_config_from_values
from custom_components.haeo.core.model import ModelOutputName, Network, OutputData, OutputType
from custom_components.haeo.core.model.topology import serialize_topology
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.core.schema.util import extract_unit_parts
from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import PRICE_UNIT_SPEC
from custom_components.haeo.elements import (
    ElementDeviceName,
    ElementOutputName,
    collect_element_subentries,
    get_element_configs,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.repairs import dismiss_optimization_failure_issue

from . import network as network_module

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
    from custom_components.haeo.core.data.input_store import InputStore
    from custom_components.haeo.elements import InputFieldPath

_LOGGER = logging.getLogger(__name__)


class ForecastPoint(TypedDict):
    """Single point in a forecast time series.

    Attributes:
        time: Timestamp as datetime object (timezone-aware)
        value: Forecast value (numeric or other types depending on output type)

    """

    time: datetime
    value: Any


@dataclass(frozen=True, slots=True)
class CoordinatorOutput:
    """Processed output ready for Home Assistant entities."""

    type: OutputType
    unit: str | None
    state: StateType | None
    forecast: list[ForecastPoint] | None
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
    currency prefix. Falls back to the configured currency when no price entity
    is found, and then ``$`` if no configured currency is available.
    """
    for state in source_states.values():
        unit = state.attributes.get("unit_of_measurement")
        if isinstance(unit, str):
            for spec in PRICE_UNIT_SPEC:
                parts = extract_unit_parts(unit, spec)
                if parts is not None:
                    return parts[0]
    return fallback_currency or "$"


def _localize_currency(unit: str | None, currency_sym: str) -> str | None:
    """Replace the ``$`` placeholder in a unit string with the detected currency symbol.

    The model and adapter layers use ``$`` as a conventional placeholder for
    monetary values (e.g. ``$/kWh``, ``$/kW``, ``$``).  At the coordinator
    boundary we substitute it with the currency symbol detected from the
    user's price sensor data so that sensors display correctly.
    """
    if unit is None:
        return None
    return unit.replace("$", currency_sym)


def _build_coordinator_output(
    output_name: ElementOutputName,
    output_data: OutputData,
    *,
    forecast_times: tuple[float, ...] | None,
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

    The forecast_times tuple contains n+1 timestamps (all boundaries).
    Each output type zips its values with however many timestamps it needs.

    Example with 3 periods of 300 seconds starting at t=0:
      - forecast_times: [0, 300, 600, 900] (n+1 = 4 boundaries)
      - Interval values (n=3): zip with [0, 300, 600]
      - Boundary values (n=4): zip with [0, 300, 600, 900]
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

    if forecast_times and len(values) > 1:
        try:
            # Convert timestamps to localized datetime objects using HA's configured timezone
            local_tz = dt_util.get_default_time_zone()
            # Zip values with available timestamps - interval values use n_periods timestamps,
            # boundary values use all n_periods+1 timestamps (strict=False handles both)
            forecast = [
                ForecastPoint(time=datetime.fromtimestamp(timestamp, tz=local_tz), value=value)
                for timestamp, value in zip(forecast_times, values, strict=False)
            ]
        except ValueError:
            forecast = None

    return CoordinatorOutput(
        type=output_data.type,
        unit=_localize_currency(output_data.unit, currency_sym),
        state=state,
        forecast=forecast,
        direction=output_data.direction,
        entity_category=(
            EntityCategory.DIAGNOSTIC
            if output_name == OUTPUT_NAME_OPTIMIZATION_DURATION or output_data.type == OutputType.SHADOW_PRICE
            else None
        ),
        device_class=DEVICE_CLASS_MAP.get(output_data.type),
        state_class=STATE_CLASS_MAP.get(output_data.type),
        options=(STATUS_OPTIONS if output_data.type == OutputType.STATUS else None),
        advanced=output_data.advanced,
        priority=output_data.priority,
        fixed=output_data.fixed,
        display_precision=output_data.display_precision,
    )


def _build_optimization_context(
    hub_config: Mapping[str, Any],
    participant_configs: Mapping[str, ElementConfigSchema],
    input_stores: Mapping[Any, "InputStore"],
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

    # Refine config entry type to not be optional
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        # Network will be created in async_initialize().
        # Typed as Network (not optional) since it's guaranteed to exist after initialization.
        # Tests may set this manually before the first optimization.
        self.network: Network = None  # type: ignore[assignment]
        self._element_updaters: dict[str, network_module.ElementUpdater] = {}
        self.topology: dict[str, Any] = {}  # Serialized topology for frontend

        # Snapshot the participant structure (which elements exist and the shape
        # of each, including list fields like policy rules) taken from the same
        # subentry view that built the input stores. Field *values* are read live
        # from the stores at optimization time, so value edits still apply; only
        # the structure is fixed. Structural changes always trigger a reload,
        # which rebuilds both the stores and this snapshot together. Reading the
        # structure live instead would let a subentry committed during setup's
        # awaits (which schedules its own reload) leak in without matching
        # stores, breaking config assembly.
        self._participant_subentry_ids: dict[str, str] = {}  # element_name -> subentry_id

        for participant in collect_element_subentries(config_entry):
            self._participant_subentry_ids[participant.name] = participant.subentry.subentry_id

        self._participant_configs: dict[str, ElementConfigSchema] = get_element_configs(
            config_entry,
            self._participant_subentry_ids,
        )

        # Custom debouncing state
        advanced_data = config_entry.data.get(HUB_SECTION_ADVANCED, {})
        self._debounce_seconds = float(advanced_data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS))
        self._last_optimization_time: float | None = None
        self._debounce_timer: CALLBACK_TYPE | None = None
        self._pending_refresh: bool = False
        self._optimization_in_progress: bool = False  # Prevent concurrent optimizations
        self._pending_element_updates: dict[str, ElementConfigData] = {}

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

    def _get_participant_configs(self) -> dict[str, ElementConfigSchema]:
        """Return the participant structure snapshot taken at construction.

        The snapshot is consistent with the input stores: both derive from the
        same subentry view. Field values are read live from the stores, so this
        only fixes structure, which changes solely via a reload.
        """
        return self._participant_configs

    async def async_initialize(self) -> None:
        """Initialize the network and set up subscriptions.

        Must be called after the coordinator is created but before any optimizations.
        This is called from async_setup_entry after all input entities are loaded.
        """
        # Create network with loaded configurations
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            msg = "Runtime data not available"
            raise RuntimeError(msg)

        periods_seconds = runtime_data.horizon_manager.periods_seconds
        loaded_configs = self._load_from_input_stores()

        _LOGGER.debug("Initializing network with %d participants", len(loaded_configs))

        self.network, self._element_updaters = await network_module.create_network(
            self.config_entry,
            periods_seconds=periods_seconds,
            participants=loaded_configs,
        )

        # Build topology for frontend card
        element_types = {name: str(config[CONF_ELEMENT_TYPE]) for name, config in loaded_configs.items()}
        self.topology = serialize_topology(self.network, element_types=element_types)
        await network_module.evaluate_network_connectivity(
            self.hass,
            self.config_entry,
            participants=loaded_configs,
        )

        # Subscribe to input store changes
        self._subscribe_to_input_stores()

    def _get_config_entry(self) -> "HaeoConfigEntry":
        """Get the typed config entry."""
        return self.config_entry  # type: ignore[return-value]

    def _get_runtime_data(self) -> "HaeoRuntimeData | None":
        """Get runtime data from config entry, or None if not available."""
        config_entry = self._get_config_entry()
        return getattr(config_entry, "runtime_data", None)

    def _subscribe_to_input_stores(self) -> None:
        """Subscribe to value changes from input stores.

        Sets up per-store listeners so each store only updates its specific
        element's TrackedParams when its value changes.

        Also subscribes to the auto-optimize switch to control horizon manager
        pause/resume and trigger optimization on re-enable.
        """
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            return

        # Subscribe to horizon manager changes (requires full re-optimization)
        network = self.network
        horizon_manager = runtime_data.horizon_manager

        @callback
        def _on_horizon_change() -> None:
            self._handle_horizon_change(network, horizon_manager)

        horizon_manager.subscribe(_on_horizon_change)

        # Subscribe to auto-optimize switch state changes
        if runtime_data.auto_optimize_switch is not None:
            self._state_change_unsubs.append(
                async_track_state_change_event(
                    self.hass,
                    [runtime_data.auto_optimize_switch.entity_id],
                    self._handle_auto_optimize_switch_change,
                )
            )
            # Apply initial state from the switch (it may have been restored)
            self._apply_auto_optimize_state(is_enabled=runtime_data.auto_optimize_switch.is_on or False)

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
        """Handle an update to a specific element's input entities.

        The network is guaranteed to exist because it's created in async_initialize()
        before this handler is registered.
        """
        # Load the updated config for just this element
        try:
            element_config = self._load_element_config(element_name)
        except ValueError:
            _LOGGER.exception("Failed to load config for element %s due to invalid input entities", element_name)
            return

        # Defer network update until optimization time
        self._pending_element_updates[element_name] = element_config

        # Trigger optimization (with debouncing)
        self.signal_optimization_stale()

    @callback
    def _handle_horizon_change(self, network: Network, horizon_manager: HorizonManager) -> None:
        """Handle horizon manager changes.

        Updates network periods with new durations from the horizon manager,
        then triggers optimization. The period update propagates to all elements
        and segments, invalidating dependent constraints and costs.
        """
        periods_seconds = horizon_manager.periods_seconds
        periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
        network.update_periods(periods_hours)

        # Trigger optimization - _are_inputs_aligned will gate until all elements update
        self.signal_optimization_stale()

    @callback
    def _handle_auto_optimize_switch_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle auto-optimize switch state change.

        On turn-on: resume horizon manager and trigger optimization.
        On turn-off: pause horizon manager.
        """
        new_state = event.data["new_state"]
        if new_state is None:
            return

        is_enabled = new_state.state == STATE_ON
        self._apply_auto_optimize_state(is_enabled=is_enabled)

        # If turned on, trigger optimization to catch up on any changes while disabled
        if is_enabled:
            self.hass.async_create_task(self.async_run_optimization())

    def _apply_auto_optimize_state(self, *, is_enabled: bool) -> None:
        """Apply auto-optimize state to the horizon manager.

        Pauses/resumes the horizon manager based on the auto-optimize setting.
        """
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            return

        if is_enabled:
            runtime_data.horizon_manager.resume()
        else:
            runtime_data.horizon_manager.pause()

    @property
    def auto_optimize_enabled(self) -> bool:
        """Return whether automatic optimization is enabled.

        Reads from the auto-optimize switch entity stored in runtime_data.
        """
        runtime_data = self._get_runtime_data()
        if not runtime_data or not runtime_data.auto_optimize_switch:
            msg = "auto_optimize_switch not available"
            raise RuntimeError(msg)
        return runtime_data.auto_optimize_switch.is_on or False

    async def async_run_optimization(self) -> None:
        """Manually trigger optimization, bypassing debouncing and auto-optimize check."""
        if not self._are_inputs_aligned():
            _LOGGER.debug("Inputs not aligned, skipping manual optimization")
            return

        await self.async_refresh()

    @callback
    def signal_optimization_stale(self) -> None:
        """Signal that optimization results are stale and a refresh may be needed.

        Checks auto_optimize_enabled before proceeding. If disabled, does nothing.
        Handles debouncing to prevent excessive refreshes.
        """
        # Skip if auto-optimization is disabled
        if not self.auto_optimize_enabled:
            return

        # If optimization is in progress, just mark pending
        if self._optimization_in_progress:
            self._pending_refresh = True
            return

        current_time = time.time()

        # Check if we're within the cooldown period
        if self._last_optimization_time is not None:
            time_since_last = current_time - self._last_optimization_time
            if time_since_last < self._debounce_seconds:
                # Within cooldown - mark pending and ensure timer is set
                self._pending_refresh = True
                if self._debounce_timer is None:
                    remaining = self._debounce_seconds - time_since_last
                    self._debounce_timer = async_call_later(self.hass, remaining, self._debounce_timer_callback)
                return

        # Not in cooldown - check if inputs are ready and optimize immediately
        self._maybe_trigger_refresh()

    @callback
    def _debounce_timer_callback(self, _now: datetime) -> None:
        """Handle debounce timer expiration."""
        self._debounce_timer = None

        if self._pending_refresh:
            self._pending_refresh = False
            self._maybe_trigger_refresh()

    @callback
    def _maybe_trigger_refresh(self) -> None:
        """Trigger a coordinator refresh if inputs are aligned."""
        if not self._are_inputs_aligned():
            _LOGGER.debug("Inputs not aligned, skipping optimization")
            return

        # Use create_task to run the async refresh
        self.hass.async_create_task(self.async_refresh())

    def _are_inputs_aligned(self) -> bool:
        """Check if all forecast input entities have the same horizon start time.

        Scalar (non-forecast) inputs are alignment-neutral since they have no
        time-series data to align. Only forecast-based inputs must match the
        horizon manager's current start time.

        Returns True if all forecast inputs are loaded and aligned to the same horizon.
        Returns False if any forecast input is missing data or horizons don't match.
        """
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            return False

        # Get expected horizon from horizon manager
        expected_horizon = runtime_data.horizon_manager.get_forecast_timestamps()
        if not expected_horizon:
            return False
        expected_start = expected_horizon[0]

        # Check forecast input stores have values and matching horizon
        for store in runtime_data.input_stores.values():
            if not store.time_series:
                continue
            store_horizon = store.horizon_start
            if store_horizon is None:
                return False
            # Allow small floating point tolerance
            if abs(store_horizon - expected_start) > 1.0:
                return False

        return True

    def _field_values_for_element(self, element_name: str) -> dict["InputFieldPath", Any]:
        """Collect resolved field values from the element's input stores."""
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            return {}
        return {
            field_path: store.value
            for (name, field_path), store in runtime_data.input_stores.items()
            if name == element_name
        }

    def _load_element_config(self, element_name: str) -> ElementConfigData:
        """Assemble a single element's config from its input stores.

        Args:
            element_name: Name of the element to load

        Returns:
            Loaded configuration

        Raises:
            ValueError: If element not found or data unavailable

        """
        participant_configs = self._get_participant_configs()
        if element_name not in participant_configs:
            msg = f"Element '{element_name}' not found in participant configs"
            raise ValueError(msg)

        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            msg = f"Runtime data not available when loading element '{element_name}'"
            raise ValueError(msg)

        forecast_times = runtime_data.horizon_manager.get_forecast_timestamps()
        return load_element_config_from_values(
            element_name,
            participant_configs[element_name],
            self._field_values_for_element(element_name),
            forecast_times,
        )

    def _load_from_input_stores(self) -> dict[str, ElementConfigData]:
        """Assemble all element configurations from input stores.

        Substitutes each input field with its store's pre-resolved value to
        produce fully loaded ElementConfigData. No state machine is consulted.
        """
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            msg = "Runtime data not available"
            raise UpdateFailed(msg)

        forecast_times = runtime_data.horizon_manager.get_forecast_timestamps()
        return {
            name: load_element_config_from_values(
                name,
                config,
                self._field_values_for_element(name),
                forecast_times,
            )
            for name, config in self._get_participant_configs().items()
        }

    def cleanup(self) -> None:
        """Clean up coordinator resources when unloading."""
        for unsub in self._state_change_unsubs:
            unsub()
        self._state_change_unsubs.clear()

        if self._debounce_timer is not None:
            self._debounce_timer()
            self._debounce_timer = None

        self._pending_element_updates.clear()

    def _apply_pending_element_updates(self) -> None:
        """Apply all pending element updates to the network.

        Called at optimization time to batch-apply updates that were deferred
        during input entity state changes. Each element's pre-resolved updater
        re-derives values through the adapter and writes directly to the
        captured TrackedParam descriptors.
        """
        for element_name, element_config in self._pending_element_updates.items():
            updater = self._element_updaters.get(element_name)
            if updater is not None:
                updater(element_config)
        self._pending_element_updates.clear()

    async def _async_update_data(self) -> CoordinatorData:
        """Update data from input entities and run optimization."""
        # Check if optimization is already in progress
        # If so, skip this call - we'll use existing data or signal retry
        if self._optimization_in_progress:
            # Return existing data if available (may be None before first refresh)
            # The base class sets self.data to None initially (via type: ignore)
            # so we need to get it as Any first to check for None
            existing_data: Any = self.data
            if existing_data is not None:
                return existing_data
            # First run with concurrent call - raise to signal retry later
            msg = "Concurrent optimization during first refresh"
            raise UpdateFailed(msg)

        start_time = time.time()
        started_at = dt_util.utc_from_timestamp(start_time).astimezone()

        # Set flag to prevent concurrent optimization triggers from callbacks
        # This is cleared in the finally block
        self._optimization_in_progress = True

        try:
            # Mark optimization start time immediately to prevent concurrent triggers
            # This ensures debouncing works even if optimization takes a long time
            self._last_optimization_time = start_time

            # Get forecast timestamps from horizon manager
            runtime_data = self._get_runtime_data()
            if runtime_data is None:
                msg = "Runtime data not available"
                raise UpdateFailed(msg)

            forecast_timestamps = runtime_data.horizon_manager.get_forecast_timestamps()

            # Build optimization context capturing all inputs for reproducibility
            context = _build_optimization_context(
                hub_config=self.config_entry.data,
                participant_configs=self._get_participant_configs(),
                input_stores=runtime_data.input_stores,
                horizon_manager=runtime_data.horizon_manager,
            )

            # Verify all store-backed inputs are available before proceeding.
            # When any input is unavailable the optimization is skipped, matching
            # the behaviour during initial setup where the integration stays in
            # the "not ready" state until every store can supply data.
            for (name, _field_path), store in runtime_data.input_stores.items():
                if not store.available:
                    msg = f"Element '{name}' has unavailable inputs"
                    raise UpdateFailed(msg)

            # Load element configurations from input stores
            # All input stores are guaranteed to be fully loaded by the time we get here
            loaded_configs = self._load_from_input_stores()

            _LOGGER.debug("Running optimization with %d participants", len(loaded_configs))

            # Network should have been created in async_initialize() or set manually in tests.
            network = self.network

            # Apply any pending element updates before optimization
            self._apply_pending_element_updates()

            # Perform the optimization
            cost = await self.hass.async_add_executor_job(network.optimize)

            end_time = time.time()
            optimization_duration = end_time - start_time

            # Record optimization time for debouncing
            self._last_optimization_time = end_time

            _LOGGER.debug("Optimization completed successfully with cost: %s", cost)
            dismiss_optimization_failure_issue(self.hass, self.config_entry.entry_id)

            network_output_data: dict[NetworkOutputName, OutputData] = {
                OUTPUT_NAME_OPTIMIZATION_COST: OutputData(type=OutputType.COST, unit="$", values=(cost,)),
                OUTPUT_NAME_OPTIMIZATION_STATUS: OutputData(
                    type=OutputType.STATUS, unit=None, values=(OPTIMIZATION_STATUS_SUCCESS,)
                ),
                OUTPUT_NAME_OPTIMIZATION_DURATION: OutputData(
                    type=OutputType.DURATION, unit=UnitOfTime.SECONDS, values=(optimization_duration,)
                ),
            }

            # Load the network subentry name from translations
            translations = await async_get_translations(
                self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
            )
            network_subentry_name = translations[f"component.{DOMAIN}.common.network_subentry_name"]

            currency_sym = detect_currency_symbol(
                context.source_states,
                fallback_currency=self.hass.config.currency,
            )

            outputs: dict[str, SubentryDevices] = {
                # HAEO outputs use network subentry name as key, network element type as device
                network_subentry_name: {
                    ELEMENT_TYPE_NETWORK: {
                        name: _build_coordinator_output(name, output, forecast_times=None, currency_sym=currency_sym)
                        for name, output in network_output_data.items()
                    }
                }
            }

            # Build nested outputs structure from all network model elements
            model_outputs: dict[str, Mapping[ModelOutputName, OutputData]] = {
                element_name: element.outputs() for element_name, element in network.elements.items()
            }

            # Process each config element using its outputs function to transform model outputs into device outputs
            for element_name, element_config in context.participants.items():
                element_type = element_config[CONF_ELEMENT_TYPE]
                outputs_fn = ELEMENT_TYPES[element_type].outputs

                # outputs function returns {device_name: {output_name: OutputData}}
                # May return multiple devices per config element (e.g., battery regions)
                try:
                    adapter_outputs: Mapping[ElementDeviceName, Mapping[ElementOutputName, OutputData]] = outputs_fn(
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

                # Process each device's outputs, grouping under the subentry (element_name)
                subentry_devices: SubentryDevices = {}
                for device_name, device_outputs in adapter_outputs.items():
                    processed_outputs: dict[ElementOutputName, CoordinatorOutput] = {
                        output_name: _build_coordinator_output(
                            output_name,
                            output_data,
                            forecast_times=forecast_timestamps,
                            currency_sym=currency_sym,
                        )
                        for output_name, output_data in device_outputs.items()
                    }

                    if processed_outputs:
                        subentry_devices[device_name] = processed_outputs

                if subentry_devices:
                    outputs[element_name] = subentry_devices

            completed_at = dt_util.utc_from_timestamp(end_time).astimezone()

            return CoordinatorData(
                context=context,
                outputs=outputs,
                started_at=started_at,
                completed_at=completed_at,
            )
        finally:
            # Always clear the in-progress flag
            self._optimization_in_progress = False
            # Clear pending flag - the next state change will trigger a new optimization
            self._pending_refresh = False


__all__ = [
    "STATUS_OPTIONS",
    "CoordinatorData",
    "CoordinatorOutput",
    "ForecastPoint",
    "HaeoDataUpdateCoordinator",
    "OptimizationContext",
    "_build_coordinator_output",
    "_build_optimization_context",
]
