"""Number entity for HAEO input configuration."""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.util import async_update_subentry_value


class ConfigEntityMode(Enum):
    """Operating mode for config entities."""

    EDITABLE = "editable"  # User can set value, no external source
    DRIVEN = "driven"  # Value driven by external entity


class HaeoInputNumber(NumberEntity):
    """Number entity representing a configurable input parameter.

    This entity serves as an intermediate layer between external sensors
    and the optimization model. It can operate in two modes:

    - EDITABLE: User can directly set the value. Used when config contains
      a static value rather than an entity ID.
      Value is persisted to config entry and survives restarts.
    - DRIVEN: Value is driven by an external sensor. Used when config
      contains an entity ID. In this mode, user edits are ignored.

    Both modes provide a forecast attribute with values across the time horizon.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HaeoConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo[NumberEntityDescription],
        device_entry: DeviceEntry,
        horizon_manager: HorizonManager,
    ) -> None:
        """Initialize the input number entity."""
        self._hass = hass
        self._config_entry: HaeoConfigEntry = config_entry
        self._subentry = subentry
        self._field_info = field_info
        self._horizon_manager = horizon_manager

        # Set device_entry to link entity to device
        self.device_entry = device_entry

        # Determine mode from config value type
        # Entity IDs can be list[str] (new format) or str (v0.1 format)
        # Constants are stored as float from NumberSelector
        config_value = subentry.data.get(field_info.field_name)

        if isinstance(config_value, list) and config_value:
            # DRIVEN mode: value comes from external sensors (list format)
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_ids: list[str] = config_value
            self._attr_native_value = None  # Will be set when data loads
        elif isinstance(config_value, str):
            # DRIVEN mode: v0.1 format - single entity ID string
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_ids = [config_value]
            self._attr_native_value = None  # Will be set when data loads
        else:
            # EDITABLE mode: value is a constant
            # Config flow ensures fields in subentry.data are either entity IDs or scalars
            self._entity_mode = ConfigEntityMode.EDITABLE
            self._source_entity_ids = []
            self._attr_native_value = float(config_value)  # type: ignore[arg-type]

        # Unique ID for multi-hub safety: entry_id + subentry_id + field_name
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"

        # Use entity description directly from field info
        self.entity_description = field_info.entity_description

        # Pass subentry data as translation placeholders
        self._attr_translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        # Build base extra state attributes (static values)
        self._base_extra_attrs: dict[str, Any] = {
            "config_mode": self._entity_mode.value,
            "element_name": subentry.title,
            "element_type": subentry.subentry_type,
            "field_name": field_info.field_name,
            "output_type": field_info.output_type,
            "time_series": field_info.time_series,
        }
        if self._source_entity_ids:
            self._base_extra_attrs["source_entities"] = self._source_entity_ids
        if field_info.direction:
            self._base_extra_attrs["direction"] = field_info.direction
        self._attr_extra_state_attributes = dict(self._base_extra_attrs)

        # Loader for time series data
        self._loader = TimeSeriesLoader()

        # Event that signals data is ready for coordinator access
        self._data_ready = asyncio.Event()

        # Captured source states for diagnostics reproducibility
        self._captured_source_states: dict[str, State] = {}

    def _get_forecast_timestamps(self) -> tuple[float, ...]:
        """Get forecast timestamps from horizon manager."""
        return self._horizon_manager.get_forecast_timestamps()

    async def async_added_to_hass(self) -> None:
        """Set up state tracking and load initial data.

        For EDITABLE mode entities, this updates the forecast in memory
        synchronously. For DRIVEN mode entities, this awaits data loading
        from source sensors, ensuring the entity is ready for coordinator
        access after async_block_till_done() completes.
        """
        await super().async_added_to_hass()

        # Subscribe to horizon manager for consistent time windows
        self.async_on_remove(self._horizon_manager.subscribe(self._handle_horizon_change))

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Update forecast for initial value
            self._update_editable_forecast()
        else:
            # Subscribe to source entity changes for DRIVEN mode
            self.async_on_remove(
                async_track_state_change_event(
                    self._hass,
                    self._source_entity_ids,
                    self._handle_source_state_change,
                )
            )
            # Load initial data - await ensures entity is ready when added_to_hass completes
            await self._async_load_data()

    @callback
    def _handle_horizon_change(self) -> None:
        """Handle horizon change - refresh forecast with new time windows."""
        if self._entity_mode == ConfigEntityMode.EDITABLE:
            self._update_editable_forecast()
            self.async_write_ha_state()
        else:
            # Re-load data and push state for driven mode
            self._hass.async_create_task(self._async_load_data_and_update())

    @callback
    def _handle_source_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle source entity state change."""
        self._hass.async_create_task(self._async_load_data_and_update())

    async def _async_load_data_and_update(self) -> None:
        """Load data and write state update."""
        await self._async_load_data()
        self.async_write_ha_state()

    async def _async_load_data(self) -> None:
        """Load data from source entities and update attributes.

        This method updates _attr_native_value and _attr_extra_state_attributes
        but does NOT call async_write_ha_state().

        During normal update flows (e.g., _async_load_data_and_update() or
        tasks scheduled from horizon-change handlers), callers should call
        async_write_ha_state() after this method returns to publish the new
        state. Do not write state from async_added_to_hass(); Home Assistant
        will handle initial state once the entity has been fully added.
        """
        # Capture source states before loading - these are the exact states the loader will use
        self._captured_source_states = {
            eid: state for eid in self._source_entity_ids if (state := self._hass.states.get(eid)) is not None
        }

        forecast_timestamps = self._get_forecast_timestamps()

        try:
            if self._field_info.boundaries:
                # Boundary fields: n+1 values at time boundaries
                values = await self._loader.load_boundaries(
                    hass=self._hass,
                    value=self._source_entity_ids,
                    forecast_times=list(forecast_timestamps),
                )
            else:
                # Interval fields: n values for periods between boundaries
                values = await self._loader.load_intervals(
                    hass=self._hass,
                    value=self._source_entity_ids,
                    forecast_times=list(forecast_timestamps),
                )
        except Exception:
            # If loading fails, don't update state
            return

        if not values:
            return

        # Build forecast as list of ForecastPoint-style dicts.
        # For boundaries: n+1 values at each timestamp
        # For intervals: n values corresponding to periods (use timestamps[:-1])
        local_tz = dt_util.get_default_time_zone()
        if self._field_info.boundaries:
            forecast = [
                {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": val}
                for ts, val in zip(forecast_timestamps, values, strict=True)
            ]
        else:
            forecast = [
                {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": val}
                for ts, val in zip(forecast_timestamps[:-1], values, strict=True)
            ]

        # Build updated extra state attributes
        extra_attrs = dict(self._base_extra_attrs)
        extra_attrs["forecast"] = forecast

        # Update native value to current (first) value
        self._attr_native_value = values[0]
        self._attr_extra_state_attributes = extra_attrs

        # Signal that data is ready
        self._data_ready.set()

    def _update_editable_forecast(self) -> None:
        """Update forecast attribute for editable mode with constant value."""
        forecast_timestamps = self._get_forecast_timestamps()

        extra_attrs = dict(self._base_extra_attrs)

        if self._attr_native_value is not None:
            # Build forecast as list of ForecastPoint-style dicts with constant value.
            # For boundaries: n+1 values at each timestamp
            # For intervals: n values corresponding to periods (use timestamps[:-1])
            local_tz = dt_util.get_default_time_zone()
            if self._field_info.boundaries:
                forecast = [
                    {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": self._attr_native_value}
                    for ts in forecast_timestamps
                ]
            else:
                forecast = [
                    {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": self._attr_native_value}
                    for ts in forecast_timestamps[:-1]
                ]
            extra_attrs["forecast"] = forecast

        self._attr_extra_state_attributes = extra_attrs

        # Signal that data is ready
        self._data_ready.set()

    def is_ready(self) -> bool:
        """Return True if data has been loaded and entity is ready."""
        return self._data_ready.is_set()

    async def wait_ready(self) -> None:
        """Wait for data to be ready."""
        await self._data_ready.wait()

    @property
    def entity_mode(self) -> ConfigEntityMode:
        """Return the entity's operating mode (EDITABLE or DRIVEN)."""
        return self._entity_mode

    @property
    def horizon_start(self) -> float | None:
        """Return the first forecast timestamp, or None if not loaded."""
        forecast = self._attr_extra_state_attributes.get("forecast")
        if forecast and len(forecast) > 0:
            first_point = forecast[0]
            if isinstance(first_point, dict) and "time" in first_point:
                time_val = first_point["time"]
                if isinstance(time_val, datetime):
                    return time_val.timestamp()
        return None

    def get_values(self) -> tuple[float, ...] | None:
        """Return the forecast values as a tuple, or None if not loaded."""
        forecast = self._attr_extra_state_attributes.get("forecast")
        if forecast:
            values = tuple(point["value"] for point in forecast if isinstance(point, dict) and "value" in point)
            if self.entity_description.native_unit_of_measurement == PERCENTAGE:
                return tuple(float(value) / 100.0 for value in values)
            return values
        return None

    def get_captured_source_states(self) -> dict[str, State]:
        """Return the source sensor states captured at last data load.

        These states represent the exact inputs that were processed to produce
        the current forecast values. For diagnostics reproducibility.
        """
        return dict(self._captured_source_states)

    async def async_set_native_value(self, value: float) -> None:
        """Handle user setting a value.

        In DRIVEN mode, user changes are effectively ignored because the
        source entity will overwrite with its value.

        In EDITABLE mode, the value is persisted to the config entry so it
        survives restarts and is visible in reconfigure flows.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            # Read-only in driven mode, but we still update to avoid confusion
            self.async_write_ha_state()
            return

        self._attr_native_value = value
        self._update_editable_forecast()
        self.async_write_ha_state()

        # Persist to config entry so value survives restarts and shows in reconfigure
        await async_update_subentry_value(
            self._hass,
            self._config_entry,
            self._subentry,
            self._field_info.field_name,
            value,
        )


__all__ = ["ConfigEntityMode", "HaeoInputNumber"]
