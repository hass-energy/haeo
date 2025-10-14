"""Data update coordinator for the Home Assistant Energy Optimization integration."""

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from pulp import value

from .const import (
    ATTR_POWER,
    CONF_HORIZON_HOURS,
    CONF_OPTIMIZER,
    CONF_PARTICIPANTS,
    CONF_PERIOD_MINUTES,
    DEFAULT_OPTIMIZER,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_PENDING,
    OPTIMIZATION_STATUS_SUCCESS,
    OPTIMIZER_NAME_MAP,
)
from .data import load_network
from .model import Network

_LOGGER = logging.getLogger(__name__)


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
        self.config = entry.data
        self.network: Network | None = None
        self.optimization_result: dict[str, Any] | None = None
        self.optimization_status = OPTIMIZATION_STATUS_PENDING
        self._last_optimization_duration: float | None = None
        self._state_change_unsub: Callable[[], None] | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

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
                # Schedule an immediate refresh
                self.hass.async_create_task(self.async_refresh())

            # Track state changes for all relevant entities
            self._state_change_unsub = async_track_state_change_event(
                self.hass,
                list(entity_ids),
                _state_change_listener,
            )

    def cleanup(self) -> None:
        """Clean up coordinator resources."""
        if self._state_change_unsub is not None:
            _LOGGER.debug("Unsubscribing from state change listeners")
            self._state_change_unsub()
            self._state_change_unsub = None

    def get_future_timestamps(self) -> list[str]:
        """Get list of ISO timestamps for each optimization period."""
        if not self.optimization_result or not self.network:
            return []

        start_time = self.optimization_result["timestamp"]
        timestamps = []

        for i in range(self.network.n_periods):
            period_time = start_time + timedelta(seconds=self.network.period * i)
            timestamps.append(period_time.isoformat())

        return timestamps

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data from Home Assistant entities and run optimization."""
        # Start timing the entire optimization process
        start_time = time.time()

        try:
            # Calculate time parameters from configuration
            period_seconds, n_periods = _calculate_time_parameters(
                self.config[CONF_HORIZON_HOURS],
                self.config[CONF_PERIOD_MINUTES],
            )

            # Build network (raises ValueError when data missing)
            try:
                self.network = await load_network(
                    self.hass,
                    self.entry,
                    period_seconds=period_seconds,
                    n_periods=n_periods,
                )
            except ValueError as err:
                self.optimization_status = OPTIMIZATION_STATUS_FAILED
                _LOGGER.warning("Required sensor / forecast data not available: %s", err)
                end_time = time.time()
                self._last_optimization_duration = end_time - start_time
                return {"cost": None, "timestamp": dt_util.utcnow(), "duration": self.last_optimization_duration}

            # Run optimization in executor job to avoid blocking the event loop
            # Network must be initialized at this point (load_network succeeded above)
            if self.network is None:
                msg = "Network was not properly initialized"
                raise RuntimeError(msg)

            optimizer_key = self.config.get(CONF_OPTIMIZER, DEFAULT_OPTIMIZER)
            optimizer_name = OPTIMIZER_NAME_MAP.get(optimizer_key, optimizer_key)
            _LOGGER.debug(
                "Running optimization for network with %d elements using %s solver",
                len(self.network.elements),
                optimizer_name,
            )
            cost = await self.hass.async_add_executor_job(self.network.optimize, optimizer_name)

            # End timing after successful optimization
            end_time = time.time()
            self._last_optimization_duration = end_time - start_time

            self.optimization_result = {
                "cost": cost,
                "timestamp": dt_util.utcnow(),
                "duration": self.last_optimization_duration,
            }
            self.optimization_status = OPTIMIZATION_STATUS_SUCCESS

            _LOGGER.debug(
                "Optimization completed successfully with cost: %s in %.3f seconds",
                cost,
                self.last_optimization_duration,
            )

        except Exception as err:
            # End timing even when optimization fails
            end_time = time.time()
            self._last_optimization_duration = end_time - start_time

            # If any exception occurs, mark the optimisation as failed and return a placeholder result
            self.optimization_status = OPTIMIZATION_STATUS_FAILED
            # Use error() with conditional exc_info instead of exception() to avoid always showing traceback
            _LOGGER.error("Optimization failed: %s", err, exc_info=_LOGGER.isEnabledFor(logging.DEBUG))  # noqa: TRY400
            self.optimization_result = None
            return {"cost": None, "timestamp": dt_util.utcnow(), "duration": self.last_optimization_duration}

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
        if hasattr(element, "power") and element.power is not None:
            # Connections have a single power attribute (net flow)
            element_data[ATTR_POWER] = extract_values(element.power)
        elif (hasattr(element, "power_consumption") and element.power_consumption is not None) or (
            hasattr(element, "power_production") and element.power_production is not None
        ):
            # Elements can have consumption, production, or both
            consumption = (
                extract_values(element.power_consumption)
                if hasattr(element, "power_consumption") and element.power_consumption is not None
                else None
            )
            production = (
                extract_values(element.power_production)
                if hasattr(element, "power_production") and element.power_production is not None
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
