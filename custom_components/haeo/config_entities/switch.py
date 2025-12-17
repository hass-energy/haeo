"""Switch entity for HAEO configurable boolean values."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.schema.fields import FieldMeta

from .mode import ConfigEntityMode


class HaeoConfigSwitch(  # pyright: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[HaeoDataUpdateCoordinator], RestoreEntity, SwitchEntity
):
    """Switch entity for HAEO boolean config fields.

    These entities provide adjustable boolean values for element configuration.
    They are created for all boolean config fields on each element device.

    Operating Modes:
        Driven: User provided external entity in config. Switch displays the
            loaded value. Changes are overwritten by coordinator updates.

        Editable: User provides input via this switch. The user's value is
            preserved and used for optimization.

        Disabled: Optional field not currently active.

    Enabled/disabled behavior:
        - provided && required: entity enabled, mode=Driven
        - provided && !required: entity enabled, mode=Driven
        - !provided && required: entity enabled, mode=Editable
        - !provided && !required: entity disabled by default, mode=Disabled
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        device_entry: DeviceEntry,
        *,
        field_meta: FieldMeta,
        config_field: str,
        translation_key: str,
        unique_id: str,
        element_name: str,
        element_type: str,
        input_name: str,
        entity_provided: bool,
        required: bool,
        default_value: bool | None = None,
        initial_value: bool | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize the config switch entity.

        Args:
            coordinator: The data update coordinator.
            device_entry: The device this entity belongs to.
            field_meta: Field metadata.
            config_field: The configuration field key.
            translation_key: The translation key for entity naming.
            unique_id: Unique ID for this entity.
            element_name: Name of the element this config entity belongs to.
            element_type: Type of the element (e.g., 'photovoltaics').
            input_name: The input name (e.g., 'photovoltaics_curtailment').
            entity_provided: Whether user provided an external entity in config.
            required: Whether the field is required.
            default_value: Default value when no entity is provided.
            initial_value: Optional initial value from config (used when config has a bool).
            translation_placeholders: Optional translation placeholders.

        """
        super().__init__(coordinator)

        self._field_meta = field_meta
        self._config_field = config_field
        self._element_name = element_name
        self._element_type = element_type
        self._input_name = input_name
        self._entity_provided = entity_provided

        self._attr_unique_id = unique_id
        self._attr_translation_key = translation_key
        self._attr_device_info = {"identifiers": device_entry.identifiers}

        # Set initial value: prefer config value, fall back to default
        if initial_value is not None:
            self._attr_is_on = initial_value
        else:
            self._attr_is_on = default_value if default_value is not None else False

        if translation_placeholders is not None:
            self._attr_translation_placeholders = translation_placeholders

        # Determine enabled state:
        # If entity provided → enabled (Driven mode)
        # If initial value or required → enabled (Editable mode)
        # If no entity && !required && no initial value → disabled (Disabled mode)
        if entity_provided or required or initial_value is not None:
            self._attr_entity_registry_enabled_default = True
        else:
            self._attr_entity_registry_enabled_default = False

    @property
    def config_mode(self) -> ConfigEntityMode:
        """Get the current operating mode of this entity."""
        if self.registry_entry is not None and self.registry_entry.disabled_by:
            return ConfigEntityMode.DISABLED

        if self._entity_provided:
            return ConfigEntityMode.DRIVEN

        return ConfigEntityMode.EDITABLE

    async def async_added_to_hass(self) -> None:
        """Restore last state when added to Home Assistant."""
        await super().async_added_to_hass()

        # Restore previous state if available (for Editable mode)
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON

        # If coordinator already has data, update our state with it
        if self.coordinator.data:
            self._handle_coordinator_update()

    async def async_turn_on(self, **_kwargs: object) -> None:
        """Turn the switch on.

        In Editable mode: stores the new value and triggers refresh.
        In Driven mode: value is ignored - entity is controlled by external source.
        """
        if self.config_mode == ConfigEntityMode.DRIVEN:
            # In Driven mode, the value is controlled externally
            return

        self._attr_is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_kwargs: object) -> None:
        """Turn the switch off.

        In Editable mode: stores the new value and triggers refresh.
        In Driven mode: value is ignored - entity is controlled by external source.
        """
        if self.config_mode == ConfigEntityMode.DRIVEN:
            # In Driven mode, the value is controlled externally
            return

        self._attr_is_on = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        In Driven mode: Update value from loaded data.
        In Editable mode: Keep user value.
        """
        # Build extra state attributes matching sensor format for visualization compatibility
        attrs: dict[str, Any] = {
            "config_mode": self.config_mode.value,
            "element_name": self._element_name,
            "element_type": self._element_type,
            "output_name": self._input_name,
            "output_type": "switch",
            "advanced": False,
        }
        self._attr_extra_state_attributes = attrs

        # Get loaded value for this field from coordinator
        loaded_value = self._get_loaded_value()

        if loaded_value is not None and self.config_mode == ConfigEntityMode.DRIVEN:
            # In Driven mode, update the displayed value
            self._attr_is_on = bool(loaded_value)

        self.async_write_ha_state()

    def _get_loaded_value(self) -> bool | None:
        """Get the loaded value for this field from coordinator.

        Returns:
            The loaded value, or None if not available.

        """
        if self.coordinator.loaded_configs is None:
            return None

        element_config = self.coordinator.loaded_configs.get(self._element_name)
        if element_config is None:
            return None

        # Get the field value from the loaded config using the config field name
        field_value = element_config.get(self._config_field)
        if field_value is None:
            return None

        return bool(field_value)

    @property
    def input_name(self) -> str:
        """Return the input name this entity represents."""
        return self._input_name

    @property
    def config_field(self) -> str:
        """Return the configuration field name this entity represents."""
        return self._config_field

    @callback
    def get_value(self) -> bool:
        """Return the current value for use by loaders."""
        return self._attr_is_on if self._attr_is_on is not None else False


__all__ = ["HaeoConfigSwitch"]
