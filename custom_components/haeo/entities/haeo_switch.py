"""Switch entity for HAEO boolean input configuration."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.haeo_number import ConfigEntityMode
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.util import async_update_subentry_value


class HaeoInputSwitch(SwitchEntity):
    """Switch entity representing a configurable boolean parameter.

    This entity serves as an intermediate layer between external sensors
    and the optimization model. It can operate in two modes:

    - EDITABLE: User can toggle the switch. Used when config contains
      a static boolean value rather than an entity ID.
      Value is persisted to config entry and survives restarts.
    - DRIVEN: Value is driven by an external sensor. Used when config
      contains an entity ID. In this mode, user toggles are ignored.

    Both modes provide forecast timestamps for consistency with other entities.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HaeoConfigEntry,
        subentry: ConfigSubentry,
        field_name: str,
        field_info: InputFieldInfo[SwitchEntityDescription],
        device_entry: DeviceEntry,
        horizon_manager: HorizonManager,
    ) -> None:
        """Initialize the input switch entity."""
        self._hass = hass
        self._config_entry: HaeoConfigEntry = config_entry
        self._subentry = subentry
        self._field_name = field_name
        self._field_info = field_info
        self._horizon_manager = horizon_manager

        # Set device_entry to link entity to device
        self.device_entry = device_entry

        # Determine mode from config value type
        # Entity IDs are stored as str from EntitySelector
        # Boolean constants are stored as bool from BooleanSelector
        config_value = subentry.data.get(field_name)

        if isinstance(config_value, str):
            # DRIVEN mode: value comes from external sensor
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_id: str | None = config_value
            self._attr_is_on = None  # Will be set when data loads
        else:
            # EDITABLE mode: value is a boolean or None (optional field)
            self._entity_mode = ConfigEntityMode.EDITABLE
            self._source_entity_id = None
            self._attr_is_on = bool(config_value) if config_value is not None else None

        # Unique ID for multi-hub safety: entry_id + subentry_id + field_name
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_name}"

        # Use entity description directly from field info
        self.entity_description = field_info.entity_description

        # Pass subentry data as translation placeholders
        self._attr_translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        # Build base extra state attributes (static values)
        self._base_extra_attrs: dict[str, Any] = {
            "config_mode": self._entity_mode.value,
            "element_name": subentry.title,
            "element_type": subentry.subentry_type,
            "field_name": field_name,
            "output_type": field_info.output_type,
        }
        if self._source_entity_id:
            self._base_extra_attrs["source_entity"] = self._source_entity_id
        self._attr_extra_state_attributes = dict(self._base_extra_attrs)

        self._state_unsub: Callable[[], None] | None = None
        self._horizon_unsub: Callable[[], None] | None = None

        # Track whether entity has been added to HA
        self._added_to_hass = False

        # Initialize forecast immediately for EDITABLE mode entities
        # This ensures get_values() returns data before async_added_to_hass() is called
        # DRIVEN mode entities load data in async_added_to_hass() - the coordinator
        # waits for all input entities to be ready before running
        if self._entity_mode == ConfigEntityMode.EDITABLE and self._attr_is_on is not None:
            self._update_forecast()

    def _get_forecast_timestamps(self) -> tuple[float, ...]:
        """Get forecast timestamps from horizon manager."""
        return self._horizon_manager.get_forecast_timestamps()

    async def async_added_to_hass(self) -> None:
        """Set up state tracking."""
        await super().async_added_to_hass()

        # Mark entity as added
        self._added_to_hass = True

        # Subscribe to horizon manager for time window changes
        self._horizon_unsub = self._horizon_manager.subscribe(self._handle_horizon_change)

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Use field default if no config value
            if self._attr_is_on is None and self._field_info.default is not None:
                self._attr_is_on = bool(self._field_info.default)
            # Update forecast for initial value
            self._update_forecast()
        else:
            # Subscribe to source entity changes for DRIVEN mode
            if self._source_entity_id is not None:
                self._state_unsub = async_track_state_change_event(
                    self._hass,
                    [self._source_entity_id],
                    self._handle_source_state_change,
                )
            # Load initial state from source
            self._load_source_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up state tracking."""
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None
        if self._horizon_unsub is not None:
            self._horizon_unsub()
            self._horizon_unsub = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_horizon_change(self) -> None:
        """Handle horizon change - refresh forecast with new time windows."""
        if self._entity_mode == ConfigEntityMode.EDITABLE:
            self._update_forecast()
            self.async_write_ha_state()
        else:
            # Re-load source state for driven mode
            self._load_source_state()
            self.async_write_ha_state()

    @callback
    def _handle_source_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle source entity state change."""
        new_state = event.data["new_state"]
        if new_state is not None:
            self._attr_is_on = new_state.state == STATE_ON
            self._update_forecast()
            self.async_write_ha_state()

    def _load_source_state(self) -> None:
        """Load current state from source entity."""
        if self._source_entity_id is None:
            return

        state = self._hass.states.get(self._source_entity_id)
        if state is not None:
            self._attr_is_on = state.state == STATE_ON
            self._update_forecast()

    def _update_forecast(self) -> None:
        """Update forecast attribute with constant value across horizon."""
        forecast_timestamps = self._get_forecast_timestamps()

        extra_attrs = dict(self._base_extra_attrs)

        if self._attr_is_on is not None:
            # Build forecast as list of ForecastPoint-style dicts
            local_tz = dt_util.get_default_time_zone()
            forecast = [
                {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": self._attr_is_on}
                for ts in forecast_timestamps
            ]
            extra_attrs["forecast"] = forecast

        self._attr_extra_state_attributes = extra_attrs

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

    def is_ready(self) -> bool:
        """Check if entity is ready for coordinator to read values.

        Returns True when entity has been added and has loaded values.
        Returns False while still loading data.
        """
        return self._added_to_hass and self.get_values() is not None

    def get_values(self) -> tuple[bool, ...] | None:
        """Return the forecast values as a tuple, or None if not loaded."""
        forecast = self._attr_extra_state_attributes.get("forecast")
        if forecast:
            return tuple(point["value"] for point in forecast if isinstance(point, dict) and "value" in point)
        return None

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Handle user turning switch on.

        In DRIVEN mode, user changes are effectively ignored because the
        source entity will overwrite with its value.

        In EDITABLE mode, the value is persisted to the config entry so it
        survives restarts and is visible in reconfigure flows.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            self.async_write_ha_state()
            return

        self._attr_is_on = True
        self._update_forecast()
        self.async_write_ha_state()

        # Persist to config entry so value survives restarts and shows in reconfigure
        await async_update_subentry_value(
            self._hass,
            self._config_entry,
            self._subentry,
            self._field_name,
            value=True,
        )

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Handle user turning switch off.

        In DRIVEN mode, user changes are effectively ignored because the
        source entity will overwrite with its value.

        In EDITABLE mode, the value is persisted to the config entry so it
        survives restarts and is visible in reconfigure flows.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            self.async_write_ha_state()
            return

        self._attr_is_on = False
        self._update_forecast()
        self.async_write_ha_state()

        # Persist to config entry so value survives restarts and shows in reconfigure
        await async_update_subentry_value(
            self._hass,
            self._config_entry,
            self._subentry,
            self._field_name,
            value=False,
        )


__all__ = ["HaeoInputSwitch"]
