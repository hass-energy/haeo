"""Switch entity for HAEO boolean input configuration."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any  # noqa: TID251  # HA SwitchEntity.async_turn_on/off are Any-typed upstream

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import CONF_RECORD_FORECASTS
from custom_components.haeo.core.data.input_store import InputMode, InputStore
from custom_components.haeo.core.data.loader.extractors.haeo import InterpolationMode
from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.elements import InputFieldPath, find_nested_config_path
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.plot_metadata import SOURCE_ROLE_KEY, classify_source_role
from custom_components.haeo.entities.translation_placeholders import build_translation_placeholders
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.unique_id import element_unique_id

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


class HaeoInputSwitch(SwitchEntity):
    """Switch entity representing a configurable boolean parameter.

    Delegates data management to an InputStore. Booleans are stored as
    0.0/1.0 in the store and converted at the HA boundary.

    - EDITABLE: User can toggle the switch. Value persisted to config entry.
    - DRIVEN: Value driven by an external sensor's on/off state.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        config_entry: HaeoConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo[SwitchEntityDescription],
        device_entry: DeviceEntry,
        horizon_manager: HorizonManager,
        store: InputStore,
        field_path: InputFieldPath | None = None,
    ) -> None:
        """Initialize the input switch entity."""
        self._config_entry: HaeoConfigEntry = config_entry
        self._field_info = field_info
        self._field_path = (
            field_path or find_nested_config_path(subentry.data, field_info.field_name) or (field_info.field_name,)
        )
        self._horizon_manager = horizon_manager

        # Set device_entry to link entity to device
        self.device_entry = device_entry

        # Wrap the prebuilt InputStore (the system's source of truth)
        self._store = store

        # Set initial HA state from store
        self._attr_is_on = self._bool_from_store()

        # Unique ID
        field_path_key = ".".join(self._field_path)
        is_list_item_field = len(self._field_path) >= LIST_ITEM_FIELD_PATH_LENGTH
        unique_key = field_info.field_name
        if is_list_item_field or (
            len(self._field_path) == SECTION_FIELD_PATH_LENGTH
            and _field_name_is_reused_in_other_sections(
                subentry.data,
                current_section=self._field_path[0],
                field_name=field_info.field_name,
            )
        ):
            unique_key = field_path_key
        self._attr_unique_id = element_unique_id(config_entry.entry_id, subentry.subentry_id, unique_key)

        # Use entity description directly from field info
        self.entity_description = field_info.entity_description

        placeholders = build_translation_placeholders(subentry)

        # For list item fields, expose item name
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
        self._base_extra_attrs: dict[str, object] = {
            "config_mode": self._store.mode.value,
            SOURCE_ROLE_KEY: classify_source_role(self._store.mode.value, field_info.field_name),
            "element_name": subentry.title,
            "element_type": subentry.subentry_type,
            "field_name": field_info.field_name,
            "field_path": field_path_key,
            "field_type": field_info.output_type,
            "time_series": field_info.time_series,
        }
        if self._store.source_entity_ids:
            self._base_extra_attrs["source_entity"] = self._store.source_entity_ids[0]
        if field_info.calendar is not None:
            self._base_extra_attrs["calendar_projection"] = field_info.calendar.projection
        self._attr_extra_state_attributes = dict(self._base_extra_attrs)

        self._record_forecasts = config_entry.data.get(CONF_RECORD_FORECASTS, False)

        self._sync_from_store()

    def _bool_from_store(self) -> bool | None:
        """Convert the store's value to a bool, or None when unset."""
        val = self._store.native_value
        if val is None:
            return None
        return bool(val)

    def _sync_from_store(self) -> None:
        """Synchronize HA entity attributes from the store's current state."""
        self._attr_is_on = self._bool_from_store()

        extra_attrs = dict(self._base_extra_attrs)
        if self._attr_is_on is not None:
            extra_attrs["forecast"] = self._build_forecast_attribute()
            if self._field_info.time_series and not self._field_info.boundaries:
                extra_attrs["interpolation_mode"] = InterpolationMode.PREVIOUS

        self._attr_extra_state_attributes = extra_attrs

    def _build_forecast_attribute(self) -> list[dict[str, datetime | bool]]:
        """Build the forecast attribute: each period's value, or the one value over the whole horizon."""
        local_tz = dt_util.get_default_time_zone()
        if not self._field_info.time_series:
            return [
                {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": bool(self._attr_is_on)}
                for ts in self._horizon_manager.get_forecast_timestamps()
            ]
        values = self._store.display_values or ()
        timestamps = self._store.forecast_timestamps
        if not self._field_info.boundaries:
            timestamps = timestamps[:-1]
        return [
            {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": bool(value)}
            for ts, value in zip(timestamps, values, strict=True)
        ]

    async def async_added_to_hass(self) -> None:
        """Show the store's value, and follow it and the horizon as they change.

        The input loaders load the store, so this entity only displays it.
        """
        await super().async_added_to_hass()
        self._apply_recorder_attribute_filtering()
        self.async_on_remove(self._store.add_listener(self._handle_change))
        # The forecast attribute spans the horizon, which moves without the value changing
        self.async_on_remove(self._horizon_manager.subscribe(self._handle_change))
        self._sync_from_store()

    def _apply_recorder_attribute_filtering(self) -> None:
        """Apply recorder filtering to this entity's runtime state info."""
        if self._record_forecasts:
            return
        self._state_info["unrecorded_attributes"] = FORECAST_UNRECORDED_ATTRIBUTES

    @callback
    def _handle_change(self) -> None:
        """Show the store's value over the current horizon."""
        self._sync_from_store()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]  # Entity declares available as a cached_property
        """Return whether the input holds a value the optimization can use."""
        return self._store.available

    def is_ready(self) -> bool:
        """Return True if data has been loaded and entity is ready."""
        return self._store.is_ready()

    async def wait_ready(self) -> None:
        """Wait for data to be ready."""
        await self._store.wait_ready()

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Handle user turning switch on."""
        if self._store.mode == InputMode.DRIVEN:
            self.async_write_ha_state()
            return

        # Persist first, so the config holds the new value by the time the store notifies
        await self._store.persist(as_constant_value(value=True))
        self._store.set_value(value=True)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Handle user turning switch off."""
        if self._store.mode == InputMode.DRIVEN:
            self.async_write_ha_state()
            return

        # Persist first, so the config holds the new value by the time the store notifies
        await self._store.persist(as_constant_value(value=False))
        self._store.set_value(value=False)


__all__ = ["HaeoInputSwitch"]
