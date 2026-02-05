"""Data update coordinator for the Home Assistant Energy Optimizer integration."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
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
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    DEFAULT_DEBOUNCE_SECONDS,
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
from custom_components.haeo.elements import (
    ELEMENT_CONFIG_SCHEMAS,
    ELEMENT_TYPES,
    ElementConfigData,
    ElementConfigSchema,
    ElementDeviceName,
    ElementOutputName,
    collect_element_subentries,
    get_input_fields,
    is_element_config_data,
    is_element_type,
)
from custom_components.haeo.model import ModelOutputName, Network, OutputData, OutputType
from custom_components.haeo.repairs import dismiss_optimization_failure_issue
from custom_components.haeo.util.forecast_times import tiers_to_periods_seconds

from . import network as network_module

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData

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


def _build_coordinator_output(
    output_name: ElementOutputName,
    output_data: OutputData,
    *,
    forecast_times: tuple[float, ...] | None,
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
    if not values:
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
        unit=output_data.unit,
        state=state,
        forecast=forecast,
        direction=output_data.direction,
        entity_category=(EntityCategory.DIAGNOSTIC if output_name == OUTPUT_NAME_OPTIMIZATION_DURATION else None),
        device_class=DEVICE_CLASS_MAP.get(output_data.type),
        state_class=STATE_CLASS_MAP.get(output_data.type),
        options=(STATUS_OPTIONS if output_data.type == OutputType.STATUS else None),
        advanced=output_data.advanced,
    )


type SubentryDevices = dict[ElementDeviceName, dict[ElementOutputName | NetworkOutputName, CoordinatorOutput]]
type CoordinatorData = dict[str, SubentryDevices]


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

        # Build participant configs and track subentry IDs
        self._participant_configs: dict[str, ElementConfigSchema] = {}
        self._participant_subentry_ids: dict[str, str] = {}  # element_name -> subentry_id

        for participant in collect_element_subentries(config_entry):
            self._participant_configs[participant.name] = participant.config
            self._participant_subentry_ids[participant.name] = participant.subentry.subentry_id

        # Custom debouncing state
        self._debounce_seconds = float(config_entry.data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS))
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

        periods_seconds = tiers_to_periods_seconds(self.config_entry.data)
        loaded_configs = self._load_from_input_entities()

        _LOGGER.debug("Initializing network with %d participants", len(loaded_configs))

        self.network = await network_module.create_network(
            self.config_entry,
            periods_seconds=periods_seconds,
            participants=loaded_configs,
        )
        await network_module.evaluate_network_connectivity(
            self.hass,
            self.config_entry,
            participants=loaded_configs,
        )

        # Subscribe to input entity changes
        self._subscribe_to_input_entities()

    def _get_config_entry(self) -> "HaeoConfigEntry":
        """Get the typed config entry."""
        return self.config_entry  # type: ignore[return-value]

    def _get_runtime_data(self) -> "HaeoRuntimeData | None":
        """Get runtime data from config entry, or None if not available."""
        config_entry = self._get_config_entry()
        return getattr(config_entry, "runtime_data", None)

    def _subscribe_to_input_entities(self) -> None:
        """Subscribe to state changes from input entities.

        Sets up per-element callbacks so each input entity only updates
        its specific element's TrackedParams when it changes.

        Also subscribes to the auto-optimize switch to control horizon manager
        pause/resume and trigger optimization on re-enable.
        """
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            return

        # Subscribe to horizon manager changes (requires full re-optimization)
        network = self.network

        @callback
        def _on_horizon_change() -> None:
            self._handle_horizon_change(network)

        runtime_data.horizon_manager.subscribe(_on_horizon_change)

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

        # Group input entities by element name
        entities_by_element: dict[str, list[str]] = {}
        for (element_name, _field_name), entity in runtime_data.input_entities.items():
            if element_name not in entities_by_element:
                entities_by_element[element_name] = []
            entities_by_element[element_name].append(entity.entity_id)

        # Subscribe each element's entities to update only that element
        for element_name, entity_ids in entities_by_element.items():
            self._state_change_unsubs.append(
                async_track_state_change_event(
                    self.hass,
                    entity_ids,
                    self._create_element_update_callback(element_name),
                )
            )

    def _create_element_update_callback(self, element_name: str) -> Callable[[Event[EventStateChangedData]], None]:
        """Create a callback that updates a specific element when its inputs change."""

        @callback
        def element_update_callback(_event: Event[EventStateChangedData]) -> None:
            """Handle state change for a specific element's inputs."""
            self._handle_element_update(element_name)

        return element_update_callback

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
    def _handle_horizon_change(self, network: Network) -> None:
        """Handle horizon manager changes.

        Updates network periods with new durations from the horizon manager,
        then triggers optimization. The period update propagates to all elements
        and segments, invalidating dependent constraints and costs.
        """
        # Update network periods with new horizon durations
        periods_seconds = tiers_to_periods_seconds(self.config_entry.data)
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
        """Check if all input entities have the same horizon start time.

        Returns True if all inputs are loaded and aligned to the same horizon.
        Returns False if any input is missing data or horizons don't match.
        """
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            return False

        # Get expected horizon from horizon manager
        expected_horizon = runtime_data.horizon_manager.get_forecast_timestamps()
        if not expected_horizon:
            return False
        expected_start = expected_horizon[0]

        # Check all input entities have values and matching horizon
        for entity in runtime_data.input_entities.values():
            entity_horizon = entity.horizon_start
            if entity_horizon is None:
                return False
            # Allow small floating point tolerance
            if abs(entity_horizon - expected_start) > 1.0:
                return False

        return True

    def _load_element_config(self, element_name: str) -> ElementConfigData:
        """Load configuration for a single element from its input entities.

        Collects loaded values from input entities and merges them with config values.

        Args:
            element_name: Name of the element to load

        Returns:
            Loaded configuration

        Raises:
            ValueError: If element not found, data unavailable, or required field missing

        """
        if element_name not in self._participant_configs:
            msg = f"Element '{element_name}' not found in participant configs"
            raise ValueError(msg)

        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            msg = f"Runtime data not available when loading element '{element_name}'"
            raise ValueError(msg)

        element_config = self._participant_configs[element_name]
        element_type = element_config[CONF_ELEMENT_TYPE]

        if not is_element_type(element_type):
            msg = f"Invalid element type '{element_type}' for element '{element_name}'"
            raise ValueError(msg)

        # Get input field definitions for this element type
        input_field_infos = get_input_fields(element_config)

        # Collect loaded values from input entities
        loaded_values: dict[str, Any] = {}
        for field_info in input_field_infos.values():
            field_name = field_info.field_name
            key = (element_name, field_name)

            if key not in runtime_data.input_entities:
                continue

            entity = runtime_data.input_entities[key]
            values = entity.get_values()

            if values is None:
                continue

            if field_info.time_series:
                loaded_values[field_name] = np.asarray(values, dtype=float)
            else:
                loaded_values[field_name] = values[0] if values else None

        element_values: dict[str, Any] = {
            key: value for key, value in element_config.items() if key not in input_field_infos
        }
        element_values.update(loaded_values)

        schema_cls = ELEMENT_CONFIG_SCHEMAS[element_type]
        optional_keys: frozenset[str] = getattr(schema_cls, "__optional_keys__", frozenset())
        for field_info in input_field_infos.values():
            field_name = field_info.field_name
            is_required = field_name not in optional_keys
            if not is_required:
                continue
            value = element_values.get(field_name)
            if value is None:
                msg = f"Missing required field '{field_name}' for element '{element_name}'"
                raise ValueError(msg)

        if not is_element_config_data(element_values):
            msg = f"Invalid config data for element '{element_name}'"
            raise ValueError(msg)

        return element_values

    def _load_from_input_entities(self) -> dict[str, ElementConfigData]:
        """Load element configurations from input entities.

        Reads forecast values from input entities and constructs ElementConfigData
        for each element, ready for the optimization model.
        """
        runtime_data = self._get_runtime_data()
        if runtime_data is None:
            msg = "Runtime data not available"
            raise UpdateFailed(msg)

        _LOGGER.debug(
            "Loading from input entities. runtime_data.input_entities: %s", list(runtime_data.input_entities.keys())
        )

        loaded_configs: dict[str, ElementConfigData] = {}

        for element_name in self._participant_configs:
            element_config = self._load_element_config(element_name)
            loaded_configs[element_name] = element_config

        return loaded_configs

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
        during input entity state changes.
        """
        for element_config in self._pending_element_updates.values():
            network_module.update_element(self.network, element_config)
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

            # Load element configurations from input entities
            # All input entities are guaranteed to be fully loaded by the time we get here
            loaded_configs = self._load_from_input_entities()

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
                OUTPUT_NAME_OPTIMIZATION_COST: OutputData(
                    type=OutputType.COST, unit=self.hass.config.currency, values=(cost,)
                ),
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

            result: CoordinatorData = {
                # HAEO outputs use network subentry name as key, network element type as device
                network_subentry_name: {
                    ELEMENT_TYPE_NETWORK: {
                        name: _build_coordinator_output(name, output, forecast_times=None)
                        for name, output in network_output_data.items()
                    }
                }
            }

            # Build nested outputs structure from all network model elements
            model_outputs: dict[str, Mapping[ModelOutputName, OutputData]] = {
                element_name: element.outputs() for element_name, element in network.elements.items()
            }

            # Process each config element using its outputs function to transform model outputs into device outputs
            for element_name, element_config in self._participant_configs.items():
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
                        )
                        for output_name, output_data in device_outputs.items()
                    }

                    if processed_outputs:
                        subentry_devices[device_name] = processed_outputs

                if subentry_devices:
                    result[element_name] = subentry_devices

            return result
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
    "_build_coordinator_output",
]
