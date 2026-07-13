"""Number entity for HAEO input configuration."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import Event, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import CONF_RECORD_FORECASTS
from custom_components.haeo.core.data.input_store import InputMode, InputStore
from custom_components.haeo.core.schema import (
    as_constant_value,
    is_connection_target,
    is_constant_value,
    is_entity_value,
    is_none_value,
    is_schema_value,
)
from custom_components.haeo.elements import InputFieldPath, find_nested_config_path, get_nested_config_value_by_path
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.plot_metadata import SOURCE_ROLE_KEY, classify_source_role
from custom_components.haeo.ha_state_machine import HomeAssistantStateMachine
from custom_components.haeo.horizon import HorizonManager

# Attributes to exclude from recorder when forecast recording is disabled
FORECAST_UNRECORDED_ATTRIBUTES: frozenset[str] = frozenset({"forecast"})
LIST_ITEM_FIELD_PATH_LENGTH = 3
SECTION_FIELD_PATH_LENGTH = 2


def _field_name_is_reused_in_other_sections(
    subentry_data: Mapping[str, object],
    *,
    current_section: str,
    field_name: str,
) -> bool:
    """Return True when another section reuses this field name."""
    for section_key, section_data in subentry_data.items():
        if section_key == current_section or not isinstance(section_data, Mapping):
            continue
        if field_name in section_data:
            return True
    return False


class HaeoInputNumber(NumberEntity):
    """Number entity representing a configurable input parameter.

    Thin HA binding layer around an InputStore. The store (in core/) handles
    all data management. This entity handles HA lifecycle: device registration,
    unique_id, state attributes, event subscriptions, and config persistence.
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
        store: InputStore,
        field_path: InputFieldPath | None = None,
        *,
        negate: bool = False,
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

        # When True the entity surfaces the running (positive) value while the
        # backing store holds its negative. Used by surfaced policy mirrors.
        self._negate = negate

        # Suppresses reacting to store change notifications this entity itself
        # triggered, so only sibling entities sharing the store react.
        self._suppress_store_change = False

        # Set device_entry to link entity to device
        self.device_entry = device_entry

        # Wrap the prebuilt InputStore (the system's source of truth)
        self._store = store

        # Set initial native value from store
        self._attr_native_value = self._display_value(self._store.native_value)

        # Unique ID
        field_path_key = ".".join(self._field_path)
        is_list_item_field = len(self._field_path) >= LIST_ITEM_FIELD_PATH_LENGTH
        unique_key = field_info.field_name
        if is_list_item_field:
            unique_key = field_path_key
        elif len(self._field_path) == SECTION_FIELD_PATH_LENGTH and _field_name_is_reused_in_other_sections(
            subentry.data,
            current_section=self._field_path[0],
            field_name=field_info.field_name,
        ):
            unique_key = (
                f"{field_info.device_type}.{field_info.field_name}" if field_info.device_type else field_path_key
            )
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{unique_key}"

        # Use entity description directly from field info
        self.entity_description = field_info.entity_description

        # Translation placeholders
        placeholders: dict[str, str] = {}

        def format_placeholder(value: object) -> str:
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
            if isinstance(value, Mapping) and not is_schema_value(value) and not is_connection_target(value):
                for nested_key, nested_value in value.items():
                    placeholders.setdefault(nested_key, format_placeholder(nested_value))
                continue
            placeholders[key] = format_placeholder(value)
        placeholders.setdefault("name", subentry.title)

        # For list item fields, add the item's name as a placeholder
        if len(self._field_path) > 1:
            list_key, index_str, *_ = self._field_path
            try:
                items = subentry.data.get(list_key)
                if isinstance(items, (list, tuple)):
                    item = items[int(index_str)]
                    if isinstance(item, Mapping) and "name" in item:
                        placeholders["rule_name"] = str(item["name"])
            except (ValueError, IndexError, KeyError):
                pass

        self._attr_translation_placeholders = placeholders

        # Build base extra state attributes
        source_role = classify_source_role(self._store.mode.value, field_info.field_name)
        self._base_extra_attrs: dict[str, object] = {
            "config_mode": self._store.mode.value,
            SOURCE_ROLE_KEY: source_role,
            "element_name": subentry.title,
            "element_type": subentry.subentry_type,
            "field_name": field_info.field_name,
            "field_path": field_path_key,
            "field_type": field_info.output_type,
            "time_series": field_info.time_series,
        }
        if self._store.source_entity_ids:
            self._base_extra_attrs["source_entities"] = self._store.source_entity_ids
        if field_info.direction:
            self._base_extra_attrs["direction"] = field_info.direction

        # For list item fields, expose sibling fields
        if len(self._field_path) >= LIST_ITEM_FIELD_PATH_LENGTH:
            own_field = field_info.field_name
            item = get_nested_config_value_by_path(subentry.data, self._field_path[:2])
            if isinstance(item, Mapping):
                for key, value in item.items():
                    if key != own_field:
                        self._base_extra_attrs[key] = value

        self._attr_extra_state_attributes = dict(self._base_extra_attrs)

        self._record_forecasts = config_entry.data.get(CONF_RECORD_FORECASTS, False)

    @property
    def store(self) -> InputStore:
        """Return the underlying InputStore."""
        return self._store

    def _display_value(self, value: float | None) -> float | None:
        """Transform a stored value into the value surfaced by this entity."""
        if value is None:
            return None
        return -value if self._negate else value

    @contextmanager
    def _suppress_self_notifications(self) -> Iterator[None]:
        """Suppress reacting to store notifications fired by this entity's own mutation."""
        self._suppress_store_change = True
        try:
            yield
        finally:
            self._suppress_store_change = False

    async def async_added_to_hass(self) -> None:
        """Set up state tracking and load initial data."""
        await super().async_added_to_hass()
        self._apply_recorder_attribute_filtering()

        # Track store changes so entities sharing a store (e.g. a policy rule
        # surfaced on both the policy device and an element device) stay in sync.
        self.async_on_remove(self._store.add_listener(self._handle_store_change))

        # Subscribe to horizon manager for consistent time windows
        if self._uses_forecast:
            self.async_on_remove(self._horizon_manager.subscribe(self._handle_horizon_change))

        if self._store.mode == InputMode.EDITABLE:
            # Refresh to signal readiness (mirrors previous _update_editable_forecast path)
            with self._suppress_self_notifications():
                self._store.refresh()
            self._sync_from_store()
        else:
            # Subscribe to source entity changes for DRIVEN mode
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    self._store.source_entity_ids,
                    self._handle_source_state_change,
                )
            )
            # Load initial data
            await self._async_load_and_sync()

    def _apply_recorder_attribute_filtering(self) -> None:
        """Apply recorder filtering to this entity's runtime state info."""
        if self._record_forecasts:
            return
        self._state_info["unrecorded_attributes"] = FORECAST_UNRECORDED_ATTRIBUTES

    @callback
    def _handle_horizon_change(self) -> None:
        """Handle horizon change - refresh with new time windows."""
        if not self._uses_forecast:
            return
        if self._store.mode == InputMode.EDITABLE:
            with self._suppress_self_notifications():
                self._store.refresh()
            self._sync_from_store()
            self.async_write_ha_state()
        else:
            self.hass.async_create_task(self._async_load_sync_and_update())

    @callback
    def _handle_store_change(self) -> None:
        """Handle a value change made through another entity sharing this store."""
        if self._suppress_store_change:
            return
        self._sync_from_store()
        self.async_write_ha_state()

    @callback
    def _handle_source_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle source entity state change."""
        self.hass.async_create_task(self._async_load_sync_and_update())

    async def _async_load_sync_and_update(self) -> None:
        """Load data, sync attributes, and write state."""
        if await self._async_load_and_sync():
            self.async_write_ha_state()

    async def _async_load_and_sync(self) -> bool:
        """Load data from store via HA state machine and sync entity attributes.

        Returns True if loading succeeded and state was synced.
        """
        sm = HomeAssistantStateMachine(self.hass)
        with self._suppress_self_notifications():
            loaded = await self._store.async_load(sm)
        if not loaded:
            return False
        self._sync_from_store()
        return True

    def _sync_from_store(self) -> None:
        """Synchronize HA entity attributes from the store's current state."""
        self._attr_native_value = self._display_value(self._store.native_value)

        extra_attrs = dict(self._base_extra_attrs)
        if self._uses_forecast and self._store.native_value is not None:
            extra_attrs["forecast"] = self._build_forecast_attribute()
        self._attr_extra_state_attributes = extra_attrs

    def _build_forecast_attribute(self) -> list[dict[str, datetime | float | None]]:
        """Build the HA forecast attribute from store values.

        Uses the store's display values (percentage fields already scaled back
        to 0-100) paired with the loaded forecast timestamps.
        """
        if not self._uses_forecast:
            return []

        display_values = self._store.display_values
        if display_values is None:
            return []

        forecast_timestamps = self._store.forecast_timestamps
        local_tz = dt_util.get_default_time_zone()

        timestamps = forecast_timestamps if self._field_info.boundaries else forecast_timestamps[:-1]
        return [
            {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": self._display_value(val)}
            for ts, val in zip(timestamps, display_values, strict=True)
        ]

    def is_ready(self) -> bool:
        """Return True if data has been loaded and entity is ready."""
        return self._store.is_ready()

    async def wait_ready(self) -> None:
        """Wait for data to be ready."""
        await self._store.wait_ready()

    @property
    def entity_mode(self) -> InputMode:
        """Return the entity's operating mode (EDITABLE or DRIVEN)."""
        return self._store.mode

    @property
    def uses_forecast(self) -> bool:
        """Return True if this entity produces time-series forecast data."""
        return self._uses_forecast

    async def async_set_native_value(self, value: float) -> None:
        """Handle user setting a value.

        In DRIVEN mode, user changes are effectively ignored.
        In EDITABLE mode, the store is updated and persisted to config entry.
        """
        if self._store.mode == InputMode.DRIVEN:
            self.async_write_ha_state()
            return

        store_value = -value if self._negate else value
        with self._suppress_self_notifications():
            self._store.set_value(store_value)
        self._sync_from_store()

        # Persist through the store's storage binding
        await self._store.persist(as_constant_value(store_value))

        self.async_write_ha_state()


__all__ = ["HaeoInputNumber"]
