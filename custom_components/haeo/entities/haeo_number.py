"""Number entity for HAEO input configuration."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.const import CONF_RECORD_FORECASTS
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
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.util import async_update_subentry_value

FORECAST_UNRECORDED_ATTRIBUTES: frozenset[str] = frozenset({"forecast"})


class ConfigEntityMode(Enum):
    """Operating mode for config entities."""

    EDITABLE = "editable"
    DRIVEN = "driven"


class HaeoInputNumber(NumberEntity):
    """Number entity representing a configurable input parameter.

    Operates in two modes:

    - EDITABLE: User can directly set the value. Value is persisted to the
      config entry and survives restarts. Triggers re-optimization.
    - DRIVEN: Display-only. Value is loaded by the coordinator from source
      sensors and pushed via update_display(). User edits are ignored.

    Both modes receive display values from the coordinator after each
    optimization via update_display().
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

        self.device_entry = device_entry

        config_value = get_nested_config_value_by_path(subentry.data, self._field_path)

        match config_value:
            case {"type": "entity", "value": entity_ids} if isinstance(entity_ids, list):
                self._entity_mode = ConfigEntityMode.DRIVEN
                self._source_entity_ids = entity_ids
                self._attr_native_value = None
            case {"type": "constant", "value": constant}:
                self._entity_mode = ConfigEntityMode.EDITABLE
                self._source_entity_ids = []
                self._attr_native_value = float(constant)
            case {"type": "none"} | None:
                self._entity_mode = ConfigEntityMode.EDITABLE
                self._source_entity_ids = []
                self._attr_native_value = None
            case _:
                msg = f"Invalid config value for field {field_info.field_name}"
                raise RuntimeError(msg)

        field_path_key = ".".join(self._field_path)
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_path_key}"

        self.entity_description = field_info.entity_description

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
            if isinstance(value, Mapping) and not is_schema_value(value) and not is_connection_target(value):
                for nested_key, nested_value in value.items():
                    placeholders.setdefault(nested_key, format_placeholder(nested_value))
                continue
            placeholders[key] = format_placeholder(value)
        placeholders.setdefault("name", subentry.title)
        self._attr_translation_placeholders = placeholders

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

        self._record_forecasts = config_entry.data.get(CONF_RECORD_FORECASTS, False)

    async def async_added_to_hass(self) -> None:
        """Set up entity after being added to Home Assistant."""
        await super().async_added_to_hass()
        self._apply_recorder_attribute_filtering()

    def _apply_recorder_attribute_filtering(self) -> None:
        """Apply recorder filtering to this entity's runtime state info."""
        if self._record_forecasts:
            return
        self._state_info["unrecorded_attributes"] = FORECAST_UNRECORDED_ATTRIBUTES

    @property
    def entity_mode(self) -> ConfigEntityMode:
        """Return the entity's operating mode (EDITABLE or DRIVEN)."""
        return self._entity_mode

    def update_display(self, value: Any, forecast_times: Sequence[float]) -> None:
        """Update display state from coordinator-loaded data."""
        extra_attrs = dict(self._base_extra_attrs)

        if self._field_info.time_series and value is not None:
            local_tz = dt_util.get_default_time_zone()
            try:
                values = list(value)
            except TypeError:
                values = [value]

            if self._field_info.boundaries:
                forecast = [
                    {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": val}
                    for ts, val in zip(forecast_times, values, strict=False)
                ]
            else:
                forecast = [
                    {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": val}
                    for ts, val in zip(forecast_times[:-1], values, strict=False)
                ]
            extra_attrs["forecast"] = forecast

            if values:
                self._attr_native_value = values[0]
        elif value is not None:
            self._attr_native_value = float(value) if not isinstance(value, bool) else value

        self._attr_extra_state_attributes = extra_attrs
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Handle user setting a value.

        In DRIVEN mode, user changes are effectively ignored because the
        coordinator will overwrite with the source sensor value.

        In EDITABLE mode, the value is persisted to the config entry so it
        survives restarts and is visible in reconfigure flows.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            self.async_write_ha_state()
            return

        self._attr_native_value = value
        self._update_editable_forecast()
        self.async_write_ha_state()

        await async_update_subentry_value(
            self.hass,
            self._config_entry,
            self._subentry,
            field_path=self._field_path,
            value=as_constant_value(value),
        )

    def _update_editable_forecast(self) -> None:
        """Update forecast attribute for editable mode with constant value."""
        extra_attrs = dict(self._base_extra_attrs)

        if self._attr_native_value is not None and self._field_info.time_series:
            forecast_timestamps = self._horizon_manager.get_forecast_timestamps()

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


__all__ = ["ConfigEntityMode", "HaeoInputNumber"]
