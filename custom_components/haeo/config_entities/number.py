"""Number entity for HAEO configurable values."""

from datetime import datetime
from typing import Any

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_PRICE
from custom_components.haeo.schema.fields import FieldMeta

from .mode import ConfigEntityMode


class HaeoConfigNumber(  # pyright: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[HaeoDataUpdateCoordinator], RestoreNumber
):
    """Number entity for HAEO config fields.

    These entities provide adjustable numeric values for element configuration.
    They are created for all numeric config fields on each element device.

    Operating Modes:
        Driven: User provided external entities in config. Number displays the
            combined output from those entities. Changes are overwritten by
            coordinator updates (effectively read-only).

        Editable: User provides input via this number entity. The user's value
            is preserved and used for optimization. Coordinator adds forecast
            attributes but does not change the state value.

        Disabled: Optional field not currently active. For required fields,
            being disabled triggers a repair issue.

    Enabled/disabled behavior:
        - provided && required: entity enabled, mode=Driven
        - provided && !required: entity enabled, mode=Driven
        - !provided && required: entity enabled, mode=Editable
        - !provided && !required: entity disabled by default, mode=Disabled
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

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
        default_value: float | None = None,
        initial_value: float | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize the config number entity.

        Args:
            coordinator: The data update coordinator.
            device_entry: The device this entity belongs to.
            field_meta: Field metadata.
            config_field: The configuration field key.
            translation_key: The translation key for entity naming.
            unique_id: Unique ID for this entity.
            element_name: Name of the element this config entity belongs to.
            element_type: Type of the element (e.g., 'battery', 'grid').
            input_name: The input name (e.g., 'grid_price_import').
            entity_provided: Whether user provided an external entity in config.
            required: Whether the field is required.
            default_value: Default value when no entity is provided.
            initial_value: Optional initial value from config (used when config has a float).
            translation_placeholders: Optional translation placeholders.

        """
        super().__init__(coordinator)

        self._field_meta = field_meta
        self._config_field = config_field
        self._element_name = element_name
        self._element_type = element_type
        self._input_name = input_name
        self._entity_provided = entity_provided
        self._initial_value = initial_value

        self._attr_unique_id = unique_id
        self._attr_translation_key = translation_key
        self._attr_device_info = {"identifiers": device_entry.identifiers}

        if translation_placeholders is not None:
            self._attr_translation_placeholders = translation_placeholders

        # Set number constraints
        if field_meta.min is not None:
            self._attr_native_min_value = field_meta.min
        if field_meta.max is not None:
            self._attr_native_max_value = field_meta.max
        if field_meta.step is not None:
            self._attr_native_step = field_meta.step
        if field_meta.unit is not None:
            self._attr_native_unit_of_measurement = field_meta.unit
        if field_meta.device_class is not None:
            self._attr_device_class = field_meta.device_class

        # Set initial value: prefer config value, fall back to default
        if initial_value is not None:
            self._attr_native_value = initial_value
        else:
            self._attr_native_value = default_value

        # Determine enabled state:
        # If entity provided → enabled (Driven mode - displays combined output)
        # If initial value or required → enabled (Editable mode - user input)
        # If no entity && !required && no initial value → disabled (Disabled mode - optional)
        if entity_provided or required or initial_value is not None:
            self._attr_entity_registry_enabled_default = True
        else:
            self._attr_entity_registry_enabled_default = False

    @property
    def config_mode(self) -> ConfigEntityMode:
        """Get the current operating mode of this entity.

        Mode is determined by:
        - Driven: entity was provided in config (we display combined output)
        - Editable: no entity provided, entity is enabled (user provides input)
        - Disabled: entity is disabled in registry
        """
        # Check if this entity is disabled in the registry
        if self.registry_entry is not None and self.registry_entry.disabled_by:
            return ConfigEntityMode.DISABLED

        # If user provided an external entity, this is Driven mode
        if self._entity_provided:
            return ConfigEntityMode.DRIVEN

        # User didn't provide entity and we're enabled → Editable mode
        return ConfigEntityMode.EDITABLE

    async def async_added_to_hass(self) -> None:
        """Restore last state when added to Home Assistant."""
        await super().async_added_to_hass()

        # Restore previous value if available (for Editable mode)
        last_data = await self.async_get_last_number_data()
        if last_data is not None and last_data.native_value is not None:
            self._attr_native_value = last_data.native_value

        # If coordinator already has data, update our state with it
        if self.coordinator.data:
            self._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value.

        In Editable mode: stores the new value and triggers refresh.
        In Driven mode: value is ignored - entity is controlled by external source.
        """
        if self.config_mode == ConfigEntityMode.DRIVEN:
            # In Driven mode, the value is controlled externally
            # Ignore user changes - they would be overwritten anyway
            return

        self._attr_native_value = value
        self.async_write_ha_state()

        # Trigger refresh to use new value in optimization
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        In Driven mode: Update value and forecast from loaded data.
        In Editable mode: Keep user value, still update forecast attributes.
        """
        # Get loaded value for this field from coordinator
        loaded_value = self._get_loaded_value()

        # Determine output_type based on field characteristics
        output_type = self._infer_output_type()

        # Build extra state attributes matching sensor format for visualization compatibility
        attrs: dict[str, Any] = {
            "config_mode": self.config_mode.value,
            "element_name": self._element_name,
            "element_type": self._element_type,
            "output_name": self._input_name,
            "output_type": output_type,
            "advanced": False,
        }

        # Add forecast from loaded value (if it's a time series) with proper timestamps
        if loaded_value is not None and isinstance(loaded_value, list) and len(loaded_value) > 1:
            forecast_timestamps = self.coordinator.forecast_timestamps
            if forecast_timestamps:
                # Convert timestamps to localized datetime objects
                local_tz = dt_util.get_default_time_zone()
                attrs["forecast"] = [
                    {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": v}
                    for ts, v in zip(forecast_timestamps, loaded_value, strict=False)
                ]
            else:
                # Fallback to indexed format if no timestamps available
                attrs["forecast"] = [{"time": i, "value": v} for i, v in enumerate(loaded_value)]

        self._attr_extra_state_attributes = attrs

        # In Driven mode only, update the displayed state value
        if self.config_mode == ConfigEntityMode.DRIVEN and loaded_value is not None:
            if isinstance(loaded_value, list):
                self._attr_native_value = loaded_value[0] if loaded_value else None
            else:
                self._attr_native_value = loaded_value

        self.async_write_ha_state()

    def _infer_output_type(self) -> str:
        """Infer the output type based on field characteristics."""
        # Use input name patterns to determine output type
        if "price" in self._input_name:
            return OUTPUT_TYPE_PRICE
        if "power" in self._input_name:
            return OUTPUT_TYPE_POWER
        # Default to power for energy-related inputs
        return OUTPUT_TYPE_POWER

    def _get_loaded_value(self) -> float | list[float] | None:
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

        # Return the value (could be float or list[float])
        if isinstance(field_value, (int, float)):
            return float(field_value)
        if isinstance(field_value, list):
            return [float(v) for v in field_value]

        return None

    @property
    def input_name(self) -> str:
        """Return the input name this entity represents."""
        return self._input_name

    @property
    def config_field(self) -> str:
        """Return the configuration field name this entity represents."""
        return self._config_field

    @callback
    def get_value(self) -> float | None:
        """Return the current value for use by loaders."""
        return self._attr_native_value


__all__ = ["HaeoConfigNumber"]
