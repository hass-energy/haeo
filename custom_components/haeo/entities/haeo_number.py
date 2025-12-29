"""Number entity for HAEO input configuration."""

from enum import Enum
from functools import cached_property
from typing import Any

from homeassistant.components.number import RestoreNumber
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo

from custom_components.haeo.schema.input_fields import InputFieldInfo


class ConfigEntityMode(Enum):
    """Operating mode for config entities."""

    EDITABLE = "editable"  # User can set value, no external source
    DRIVEN = "driven"  # Value driven by external entity


def _is_entity_id(value: Any) -> bool:
    """Check if a value looks like an entity ID.

    Entity IDs contain a domain separator (e.g., sensor.temperature).
    Element names and other strings don't have dots.
    """
    return isinstance(value, str) and "." in value


def _extract_source_entity_ids(config_value: Any) -> list[str]:
    """Extract entity IDs from a config value.

    Handles both single entity IDs and lists of entity IDs.
    """
    if isinstance(config_value, list):
        return [v for v in config_value if _is_entity_id(v)]
    if _is_entity_id(config_value):
        return [config_value]
    return []


class HaeoInputNumber(RestoreNumber):
    """Number entity representing a configurable input parameter.

    This entity serves as an intermediate layer between external sensors
    and the optimization model. It can operate in two modes:

    - EDITABLE: User can directly set the value. Used when config contains
      a static value rather than an entity ID.
    - DRIVEN: Value is driven by an external sensor. Used when config
      contains an entity ID. In this mode, user edits are ignored.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo,
        device_entry: DeviceEntry,
    ) -> None:
        """Initialize the input number entity.

        Args:
            hass: Home Assistant instance
            config_entry: Parent config entry (the hub)
            subentry: Config subentry for this element
            field_info: Metadata about this input field
            device_entry: Device entry to associate this entity with

        """
        self._hass = hass
        self._config_entry = config_entry
        self._subentry = subentry
        self._field_info = field_info
        self._device_entry = device_entry

        # Determine mode from config value
        config_value = subentry.data.get(field_info.field_name)
        source_entity_ids = _extract_source_entity_ids(config_value)

        if source_entity_ids:
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_ids = source_entity_ids
            self._attr_native_value = None  # Will be set by coordinator update
        else:
            self._entity_mode = ConfigEntityMode.EDITABLE
            self._source_entity_ids = []
            # Set initial value from config (may be None for optional fields)
            if config_value is not None:
                self._attr_native_value = float(config_value)
            else:
                self._attr_native_value = None

        # Unique ID for multi-hub safety: entry_id + subentry_id + field_name
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"

        # Entity attributes from field info
        self._attr_translation_key = field_info.translation_key or field_info.field_name
        self._attr_native_unit_of_measurement = field_info.unit
        self._attr_device_class = field_info.device_class
        if field_info.min_value is not None:
            self._attr_native_min_value = field_info.min_value
        if field_info.max_value is not None:
            self._attr_native_max_value = field_info.max_value
        if field_info.step is not None:
            self._attr_native_step = field_info.step

        # Pass subentry data as translation placeholders
        self._attr_translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        # Build extra state attributes
        extra_attrs: dict[str, Any] = {
            "config_mode": self._entity_mode.value,
            "element_name": subentry.title,
            "element_type": subentry.subentry_type,
            "field_name": field_info.field_name,
            "output_type": field_info.output_type,
            "time_series": field_info.time_series,
        }
        if self._source_entity_ids:
            extra_attrs["source_entities"] = self._source_entity_ids
        if field_info.direction:
            extra_attrs["direction"] = field_info.direction
        self._attr_extra_state_attributes = extra_attrs

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers=self._device_entry.identifiers)

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Restore previous value if available
            last_data = await self.async_get_last_number_data()
            if last_data and last_data.native_value is not None:
                self._attr_native_value = last_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        """Handle user setting a value.

        In DRIVEN mode, user changes are effectively ignored because the
        coordinator will overwrite with the external sensor value.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            # Read-only in driven mode, but we still update to avoid confusion
            self.async_write_ha_state()
            return

        self._attr_native_value = value
        self.async_write_ha_state()

    def get_current_value(self) -> float | None:
        """Return current value for optimization.

        This is called by the ElementInputCoordinator (Phase 2) to get
        the current input value for this field.
        """
        return self._attr_native_value


__all__ = ["ConfigEntityMode", "HaeoInputNumber"]
