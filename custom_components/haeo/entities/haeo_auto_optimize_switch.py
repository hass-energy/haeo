"""Switch entity for controlling automatic optimization."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator


class HaeoAutoOptimizeSwitch(SwitchEntity):
    """Switch entity to enable/disable automatic optimization.

    This switch controls whether HAEO automatically runs optimization
    when input entities change. When disabled, users must manually
    trigger optimization via the run_optimizer service.

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
        coordinator: HaeoDataUpdateCoordinator,
    ) -> None:
        """Initialize the auto-optimize switch entity."""
        self._hass = hass
        self._config_entry = config_entry
        self._coordinator = coordinator

        # Link to the network device
        self.device_entry = device_entry

        # Unique ID: entry_id + auto_optimize
        self._attr_unique_id = f"{config_entry.entry_id}_auto_optimize"

        # Initialize state from coordinator
        self._attr_is_on = coordinator.auto_optimize_enabled

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable automatic optimization."""
        self._coordinator.auto_optimize_enabled = True
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable automatic optimization."""
        self._coordinator.auto_optimize_enabled = False
        self._attr_is_on = False
        self.async_write_ha_state()


__all__ = ["HaeoAutoOptimizeSwitch"]
