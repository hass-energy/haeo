"""Data update coordinator for the Home Assistant Energy Optimization integration."""

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from pulp import value

from .const import (
    ATTR_POWER,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_OPTIMIZER,
    CONF_PARTICIPANTS,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_OPTIMIZER,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_PENDING,
    OPTIMIZATION_STATUS_SUCCESS,
    OPTIMIZER_NAME_MAP,
)
from .data import load_network
from .model import Network
from .repairs import (
    create_missing_sensor_issue,
    create_optimization_persistent_failure_issue,
    dismiss_optimization_failure_issue,
)

_LOGGER = logging.getLogger(__name__)


def _get_child_elements(hass: HomeAssistant, hub_entry_id: str) -> dict[str, dict[str, Any]]:
    """Get all element configs from hub's subentries.

    Args:
        hass: Home Assistant instance
        hub_entry_id: The parent hub entry ID

    Returns:
        Dictionary mapping element names to their configurations
        Note: Excludes the Network subentry (which is for optimization sensors only)

    """
    hub_entry = hass.config_entries.async_get_entry(hub_entry_id)
    if not hub_entry:
        return {}

    elements = {}
    for subentry in hub_entry.subentries.values():
        # Skip the Network subentry - it's for optimization sensors, not a participant
        if subentry.subentry_type == "network":
            continue

        name = subentry.data.get("name_value")

        # Fail loudly if required fields are missing
        if not name:
            msg = f"Subentry {subentry.subentry_id} is missing required 'name_value' field"
            raise ValueError(msg)

        # Build element config from subentry data
        # The subentry_type becomes CONF_ELEMENT_TYPE, and we include all other data
        element_config = {
            CONF_ELEMENT_TYPE: subentry.subentry_type,
            **subentry.data,
        }
        # Remove name_value since it's used as the key
        element_config.pop("name_value", None)
        elements[name] = element_config
    return elements


def _calculate_time_parameters(horizon_hours: int, period_minutes: int) -> tuple[int, int]:
    """Calculate period in seconds and number of periods from horizon and period configuration.

    Args:
        horizon_hours: Optimization horizon in hours
        period_minutes: Optimization period in minutes

    Returns:
        Tuple of (period_seconds, n_periods)

    """
    period_seconds = period_minutes * 60  # Convert minutes to seconds
    horizon_seconds = horizon_hours * 3600  # Convert hours to seconds
    n_periods = horizon_seconds // period_seconds
    return period_seconds, n_periods


def _extract_entity_ids(config: Any) -> set[str]:
    """Extract all entity IDs from participant configuration.

    Args:
        config: Configuration dictionary containing participants

    Returns:
        Set of entity IDs referenced in the configuration

    """
    entity_ids: set[str] = set()
    participants = dict(config.get(CONF_PARTICIPANTS, {}))

    for participant_config in participants.values():
        for key, field_value in participant_config.items():
            # Skip non-entity fields
            if key in ("element_type", "name"):
                continue

            # Check if it's a dict with 'value' field (this is how entity IDs are stored)
            if isinstance(field_value, dict) and "value" in field_value:
                value_content = field_value["value"]
                # Handle both single entity ID (str) and list of entity IDs
                if isinstance(value_content, str) and value_content.startswith("sensor."):
                    entity_ids.add(value_content)
                elif isinstance(value_content, list):
                    entity_ids.update(
                        eid for eid in value_content if isinstance(eid, str) and eid.startswith("sensor.")
                    )
            # Handle direct string values (for backwards compatibility or simpler config)
            elif isinstance(field_value, str) and field_value.startswith("sensor."):
                entity_ids.add(field_value)

    return entity_ids


class HaeoDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data update coordinator for HAEO integration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry

        # Build config with participants from child subentries
        self.config = {
            **entry.data,
            CONF_PARTICIPANTS: _get_child_elements(hass, entry.entry_id),
        }

        self.network: Network | None = None
        self.optimization_result: dict[str, Any] | None = None
        self.optimization_status = OPTIMIZATION_STATUS_PENDING
        self._last_optimization_duration: float | None = None
        self._state_change_unsub: Callable[[], None] | None = None
        self._debounce_cancel: Callable[[], None] | None = None
        self._pending_refresh = False
        self._update_in_progress = False

        configured_debounce = self.config.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS)
        if configured_debounce is None:
            configured_debounce = DEFAULT_DEBOUNCE_SECONDS
        self._debounce_seconds = float(configured_debounce)

        configured_interval_minutes = self.config.get(
            CONF_UPDATE_INTERVAL_MINUTES,
            DEFAULT_UPDATE_INTERVAL_MINUTES,
        )
        if configured_interval_minutes is None:
            configured_interval_minutes = DEFAULT_UPDATE_INTERVAL_MINUTES
        self._update_interval_minutes = int(configured_interval_minutes)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
            config_entry=entry,
        )

        self.update_interval = timedelta(minutes=self._update_interval_minutes)

        # Set up state change listeners for all entity IDs in configuration
        self._setup_state_change_listeners()

    def _setup_state_change_listeners(self) -> None:
        """Set up listeners for entity state changes to trigger optimization."""
        entity_ids = _extract_entity_ids(self.config)

        if entity_ids:
            _LOGGER.debug("Setting up state change listeners for %d entities", len(entity_ids))

            @callback
            def _state_change_listener(_event: Event[EventStateChangedData]) -> None:
                """Handle state changes for tracked entities."""
                _LOGGER.debug("Entity state changed, triggering optimization update")
                self._schedule_debounced_refresh()

            # Track state changes for all relevant entities
            self._state_change_unsub = async_track_state_change_event(
                self.hass,
                list(entity_ids),
                _state_change_listener,
            )

    def _schedule_debounced_refresh(self, *, immediate: bool = False) -> None:
        """Schedule an optimization refresh respecting the configured debounce."""
        if self._debounce_cancel is not None:
            self._debounce_cancel()
            self._debounce_cancel = None

        delay = 0.0 if immediate else max(0.0, self._debounce_seconds)
        self._debounce_cancel = async_call_later(self.hass, delay, self._handle_debounced_refresh)

    @callback
    def _handle_debounced_refresh(self, _now: datetime) -> None:
        """Execute a debounced refresh unless an update is already in progress."""
        self._debounce_cancel = None

        if self._update_in_progress:
            self._pending_refresh = True
            return

        def _refresh() -> None:
            """Run refresh within the event loop thread."""
            self.hass.async_create_task(self.async_refresh())

        self.hass.loop.call_soon_threadsafe(_refresh)

    def cleanup(self) -> None:
        """Clean up coordinator resources."""
        if self._debounce_cancel is not None:
            _LOGGER.debug("Cancelling pending debounced refresh")
            self._debounce_cancel()
            self._debounce_cancel = None
        if self._state_change_unsub is not None:
            _LOGGER.debug("Unsubscribing from state change listeners")
            self._state_change_unsub()
            self._state_change_unsub = None

    def check_sensors_available(self) -> tuple[bool, list[str]]:
        """Check if all configured sensors are available.

        Returns:
            Tuple of (all_available, list_of_unavailable_entity_ids)

        """
        entity_ids = _extract_entity_ids(self.config)
        unavailable = []

        for entity_id in entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                unavailable.append(entity_id)

        return len(unavailable) == 0, unavailable

    def get_future_timestamps(self) -> list[str]:
        """Get list of ISO timestamps for each optimization period."""
        if not self.optimization_result or not self.network:
            return []

        start_time = self.optimization_result["timestamp"]
        timestamps = []

        for i in range(self.network.n_periods):
            period_time = start_time + timedelta(hours=self.network.period * i)
            timestamps.append(period_time.isoformat())

        return timestamps

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data from Home Assistant entities and run optimization."""
        start_time = time.time()
        self._update_in_progress = True

        try:
            sensors_available, unavailable_sensors = self.check_sensors_available()
            if not sensors_available:
                max_display = 5
                sensor_list = ", ".join(unavailable_sensors[:max_display])
                if len(unavailable_sensors) > max_display:
                    sensor_list += "..."
                _LOGGER.info(
                    "Waiting for %d sensor(s) to become available: %s",
                    len(unavailable_sensors),
                    sensor_list,
                )
                self.optimization_status = OPTIMIZATION_STATUS_PENDING
                end_time = time.time()
                self._last_optimization_duration = end_time - start_time
                return {"cost": None, "timestamp": dt_util.utcnow(), "duration": self._last_optimization_duration}

            period_seconds, n_periods = _calculate_time_parameters(
                self.config[CONF_HORIZON_HOURS],
                self.config[CONF_PERIOD_MINUTES],
            )

            try:
                self.network = await load_network(
                    self.hass,
                    self.entry,
                    period_seconds=period_seconds,
                    n_periods=n_periods,
                    config=self.config,
                )
            except ValueError as err:
                self.optimization_status = OPTIMIZATION_STATUS_FAILED
                _LOGGER.warning("Required sensor / forecast data not available: %s", err)

                error_msg = str(err)
                if "sensor" in error_msg.lower():
                    element_name = "unknown"
                    for key in self.config.get(CONF_PARTICIPANTS, {}):
                        if key in error_msg:
                            element_name = key
                            break
                    create_missing_sensor_issue(self.hass, element_name, error_msg)

                end_time = time.time()
                self._last_optimization_duration = end_time - start_time
                return {"cost": None, "timestamp": dt_util.utcnow(), "duration": self.last_optimization_duration}

            if self.network is None:
                msg = "Network was not properly initialized"
                raise RuntimeError(msg)

            optimizer_key = self.config.get(CONF_OPTIMIZER, DEFAULT_OPTIMIZER) or DEFAULT_OPTIMIZER
            optimizer_name = OPTIMIZER_NAME_MAP.get(optimizer_key, optimizer_key)
            _LOGGER.debug(
                "Running optimization for network with %d elements using %s solver",
                len(self.network.elements),
                optimizer_name,
            )
            cost = await self.hass.async_add_executor_job(self.network.optimize, optimizer_name)

            end_time = time.time()
            self._last_optimization_duration = end_time - start_time

            self.optimization_result = {
                "cost": cost,
                "timestamp": dt_util.utcnow(),
                "duration": self.last_optimization_duration,
            }
            self.optimization_status = OPTIMIZATION_STATUS_SUCCESS

            dismiss_optimization_failure_issue(self.hass, self.entry.entry_id)

            _LOGGER.debug(
                "Optimization completed successfully with cost: %s in %.3f seconds",
                cost,
                self.last_optimization_duration,
            )

        except Exception as err:
            end_time = time.time()
            self._last_optimization_duration = end_time - start_time
            self.optimization_status = OPTIMIZATION_STATUS_FAILED

            create_optimization_persistent_failure_issue(
                self.hass,
                self.entry.entry_id,
                str(err),
            )

            _LOGGER.error("Optimization failed: %s", err, exc_info=_LOGGER.isEnabledFor(logging.DEBUG))  # noqa: TRY400
            self.optimization_result = None
            return {"cost": None, "timestamp": dt_util.utcnow(), "duration": self.last_optimization_duration}

        finally:
            self._update_in_progress = False
            if self._pending_refresh:
                self._pending_refresh = False
                self._schedule_debounced_refresh(immediate=True)

        return self.optimization_result

    def get_element_data(self, element_name: str) -> dict[str, Any] | None:
        """Get data for a specific element directly from the network."""
        if not self.network or element_name not in self.network.elements:
            return None

        element = self.network.elements[element_name]
        element_data: dict[str, Any] = {}

        # Helper to extract values safely
        def extract_values(variables: Sequence[Any]) -> list[float]:
            result = []
            for var in variables:
                val = value(var)  # type: ignore[no-untyped-call]
                result.append(float(val) if isinstance(val, (int, float)) else 0.0)
            return result

        # Get power values (net power, can be positive or negative)
        if hasattr(element, "power") and element.power is not None:  # type: ignore[attr-defined]
            # Connections have a single power attribute (net flow)
            element_data[ATTR_POWER] = extract_values(element.power)  # type: ignore[arg-type]
        elif (hasattr(element, "power_consumption") and element.power_consumption is not None) or (  # type: ignore[attr-defined]
            hasattr(element, "power_production") and element.power_production is not None  # type: ignore[attr-defined]
        ):
            # Elements can have consumption, production, or both
            consumption = (
                extract_values(element.power_consumption)  # type: ignore[arg-type]
                if hasattr(element, "power_consumption") and element.power_consumption is not None  # type: ignore[attr-defined]
                else None
            )
            production = (
                extract_values(element.power_production)  # type: ignore[arg-type]
                if hasattr(element, "power_production") and element.power_production is not None  # type: ignore[attr-defined]
                else None
            )

            # Calculate net power based on what's available
            if consumption is not None and production is not None:
                # Both consumption and production (e.g., batteries, grid)
                element_data[ATTR_POWER] = [p - c for p, c in zip(production, consumption, strict=False)]
            elif production is not None:
                # Only production (e.g., photovoltaics, solar)
                element_data[ATTR_POWER] = production
            elif consumption is not None:
                # Only consumption (e.g., loads)
                element_data[ATTR_POWER] = [-c for c in consumption]  # Negative for consumption

        if hasattr(element, "energy") and element.energy is not None:
            element_data["energy"] = extract_values(element.energy)

        return element_data if element_data else None

    @property
    def last_optimization_cost(self) -> float | None:
        """Get the last optimization cost."""
        if self.optimization_result:
            cost = self.optimization_result["cost"]
            return float(cost) if cost is not None else None
        return None

    @property
    def last_optimization_time(self) -> datetime | None:
        """Get the last optimization timestamp."""
        if self.optimization_result:
            timestamp = self.optimization_result["timestamp"]
            return timestamp if isinstance(timestamp, datetime) else None
        return None

    @property
    def last_optimization_duration(self) -> float | None:
        """Get the last optimization duration in seconds."""
        return self._last_optimization_duration
