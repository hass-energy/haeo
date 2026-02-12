"""Number entity for HAEO input configuration."""

import asyncio
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import Event, State, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import CONF_RECORD_FORECASTS
from custom_components.haeo.data.loader import ScalarLoader, TimeSeriesLoader
from custom_components.haeo.elements import InputFieldPath, find_nested_config_path, get_nested_config_value_by_path
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.schema import (
    as_constant_value,
    as_entity_value,
    is_connection_target,
    is_constant_value,
    is_entity_value,
    is_none_value,
)
from custom_components.haeo.util import async_update_subentry_value

# Attributes to exclude from recorder when forecast recording is disabled
FORECAST_UNRECORDED_ATTRIBUTES: frozenset[str] = frozenset({"forecast"})


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
        config_entry: HaeoConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo[NumberEntityDescription],
        device_entry: DeviceEntry,
        horizon_manager: HorizonManager,
        field_path: InputFieldPath | None = None,
    ) -> None:
        """Initialize the input number entity."""
        self._config_entry: HaeoConfigEntry = config_entry
        self._subentry = subentry
        self._field_info = field_info
        self._field_path = (
            field_path or find_nested_config_path(subentry.data, field_info.field_name) or (field_info.field_name,)
        )
        self._horizon_manager = horizon_manager
        self._uses_forecast = field_info.time_series

        # Set device_entry to link entity to device
        self.device_entry = device_entry

        # Determine mode from schema value type
        config_value = get_nested_config_value_by_path(subentry.data, self._field_path)

        match config_value:
            case {"type": "entity", "value": entity_ids} if isinstance(entity_ids, list):
                # DRIVEN mode: value comes from external sensors
                self._entity_mode = ConfigEntityMode.DRIVEN
                self._source_entity_ids = entity_ids
                self._attr_native_value = None  # Will be set when data loads
            case {"type": "constant", "value": constant}:
                # EDITABLE mode: value is a constant
                self._entity_mode = ConfigEntityMode.EDITABLE
                self._source_entity_ids = []
                self._attr_native_value = float(constant)
            case {"type": "none"} | None:
                # Disabled or missing configuration
                self._entity_mode = ConfigEntityMode.EDITABLE
                self._source_entity_ids = []
                self._attr_native_value = None
            case _:
                msg = f"Invalid config value for field {field_info.field_name}"
                raise RuntimeError(msg)

        # Unique ID for multi-hub safety: entry_id + subentry_id + field_name
        field_path_key = ".".join(self._field_path)
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_path_key}"

        # Use entity description directly from field info
        self.entity_description = field_info.entity_description

        # Pass subentry data as translation placeholders
        placeholders: dict[str, str] = {}

        def format_placeholder(value: Any) -> str:
            if is_entity_value(value):
                return ", ".join(value["value"])
            if is_constant_value(value):
                return str(value["value"])
            if is_none_value(value):
                return ""
            if is_connection_target(value):
                return value["value"]
            return str(value)

        for key, value in subentry.data.items():
            if isinstance(value, Mapping):
                for nested_key, nested_value in value.items():
                    placeholders.setdefault(nested_key, format_placeholder(nested_value))
                continue
            placeholders[key] = format_placeholder(value)
        placeholders.setdefault("name", subentry.title)
        self._attr_translation_placeholders = placeholders

        # Build base extra state attributes (static values)
        self._base_extra_attrs: dict[str, Any] = {
            "config_mode": self._entity_mode.value,
            "element_name": subentry.title,
            "element_type": subentry.subentry_type,
            "field_name": field_info.field_name,
            "field_path": field_path_key,
            "output_type": field_info.output_type,
            "time_series": field_info.time_series,
        }
        if self._source_entity_ids:
            self._base_extra_attrs["source_entities"] = self._source_entity_ids
        if field_info.direction:
            self._base_extra_attrs["direction"] = field_info.direction
        self._attr_extra_state_attributes = dict(self._base_extra_attrs)

        # Loaders for time series and scalar data
        self._time_series_loader = TimeSeriesLoader()
        self._scalar_loader = ScalarLoader()
        self._loader = self._time_series_loader

        # Event that signals data is ready for coordinator access
        self._data_ready = asyncio.Event()

        # Captured source states for reproducibility (populated when loading data)
        self._captured_source_states: Mapping[str, State] = {}

        # Exclude forecast from recorder unless explicitly enabled
        if not config_entry.data.get(CONF_RECORD_FORECASTS, False):
            self._unrecorded_attributes = FORECAST_UNRECORDED_ATTRIBUTES

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
        if self._uses_forecast:
            self.async_on_remove(self._horizon_manager.subscribe(self._handle_horizon_change))

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Update forecast for initial value
            self._update_editable_forecast()
        else:
            # Subscribe to source entity changes for DRIVEN mode
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    self._source_entity_ids,
                    self._handle_source_state_change,
                )
            )
            # Load initial data - await ensures entity is ready when added_to_hass completes
            await self._async_load_data()

    @callback
    def _handle_horizon_change(self) -> None:
        """Handle horizon change - refresh forecast with new time windows."""
        if not self._uses_forecast:
            return
        if self._entity_mode == ConfigEntityMode.EDITABLE:
            self._update_editable_forecast()
            self.async_write_ha_state()
        else:
            # Re-load data and push state for driven mode
            self.hass.async_create_task(self._async_load_data_and_update())

    @callback
    def _handle_source_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle source entity state change."""
        self.hass.async_create_task(self._async_load_data_and_update())

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
        # Capture source states before loading for reproducibility
        self._captured_source_states = {
            eid: state for eid in self._source_entity_ids if (state := self.hass.states.get(eid)) is not None
        }

        if not self._uses_forecast:
            if not self._source_entity_ids:
                return
            try:
                scalar_value = await self._scalar_loader.load(
                    hass=self.hass,
                    value=as_entity_value(self._source_entity_ids),
                )
            except Exception:
                return

            self._attr_native_value = scalar_value
            self._attr_extra_state_attributes = dict(self._base_extra_attrs)
            self._data_ready.set()
            return

        forecast_timestamps = self._get_forecast_timestamps()

        try:
            if self._field_info.boundaries:
                # Boundary fields: n+1 values at time boundaries
                values = await self._time_series_loader.load_boundaries(
                    hass=self.hass,
                    value=as_entity_value(self._source_entity_ids),
                    forecast_times=list(forecast_timestamps),
                )
            else:
                # Interval fields: n values for periods between boundaries
                values = await self._time_series_loader.load_intervals(
                    hass=self.hass,
                    value=as_entity_value(self._source_entity_ids),
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
        extra_attrs = dict(self._base_extra_attrs)

        if self._attr_native_value is not None and self._uses_forecast:
            forecast_timestamps = self._get_forecast_timestamps()

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
        if not self._uses_forecast:
            if self._attr_native_value is None:
                return None
            value = float(self._attr_native_value)
            if self.entity_description.native_unit_of_measurement == PERCENTAGE:
                return (value / 100.0,)
            return (value,)
        forecast = self._attr_extra_state_attributes.get("forecast")
        if forecast:
            values = tuple(point["value"] for point in forecast if isinstance(point, dict) and "value" in point)
            if self.entity_description.native_unit_of_measurement == PERCENTAGE:
                return tuple(float(value) / 100.0 for value in values)
            return values
        return None

    def get_captured_source_states(self) -> Mapping[str, State]:
        """Return source states captured when data was last loaded.

        Returns:
            Dict mapping source entity IDs to their State objects at load time.
            Empty dict for EDITABLE mode entities (no source entities).

        """
        return self._captured_source_states

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
            self.hass,
            self._config_entry,
            self._subentry,
            field_path=self._field_path,
            value=as_constant_value(value),
        )


__all__ = ["ConfigEntityMode", "HaeoInputNumber"]
