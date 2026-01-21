"""Switch entity for controlling automatic optimization."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.restore_state import RestoreEntity


class AutoOptimizeSwitch(SwitchEntity, RestoreEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Switch entity to enable/disable automatic optimization.

    This switch controls whether HAEO automatically runs optimization
    when input entities change. When disabled, users must manually
    trigger optimization via the optimize service.

    Uses RestoreEntity to persist state across Home Assistant restarts.

    This is a pure state holder - the coordinator subscribes to state
    changes and reacts accordingly.

    Default: enabled (preserves current behavior)
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "network_auto_optimize"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device_entry: DeviceEntry,
    ) -> None:
        """Initialize the auto-optimize switch entity.

        This switch is a pure state holder with no coordinator knowledge.
        The coordinator subscribes to this switch's state changes.
        """
        self._hass = hass
        self._config_entry = config_entry

        # Link to the network device
        self.device_entry = device_entry

        # Unique ID: entry_id + auto_optimize
        self._attr_unique_id = f"{config_entry.entry_id}_auto_optimize"

        # Default state - will be overridden by restored state in async_added_to_hass
        self._attr_is_on = True

    async def async_added_to_hass(self) -> None:
        """Restore state when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        # Try to restore previous state
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == STATE_ON
        else:
            # No previous state - default to enabled
            self._attr_is_on = True

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable automatic optimization.

        The coordinator subscribes to this state change and will
        resume the horizon manager and trigger optimization.
        """
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable automatic optimization.

        The coordinator subscribes to this state change and will
        pause the horizon manager.
        """
        self._attr_is_on = False
        self.async_write_ha_state()


__all__ = ["AutoOptimizeSwitch"]
