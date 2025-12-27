"""Number platform for Home Assistant Energy Optimizer integration."""

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.haeo.const import (
    CONF_BLACKOUT_PROTECTION,
    DEFAULT_BLACKOUT_PROTECTION,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    NETWORK_DEVICE_NETWORK,
)

_LOGGER = logging.getLogger(__name__)

# Entity ID for the blackout slack penalty number
BLACKOUT_SLACK_PENALTY_KEY = "blackout_slack_penalty"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO number entities."""
    # Only create blackout slack penalty number if blackout protection is enabled
    blackout_protection = config_entry.data.get(CONF_BLACKOUT_PROTECTION, DEFAULT_BLACKOUT_PROTECTION)
    if not blackout_protection:
        _LOGGER.debug("Blackout protection disabled, skipping number entity setup")
        return

    # Find the Network subentry
    network_subentry = None
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == ELEMENT_TYPE_NETWORK:
            network_subentry = subentry
            break

    if network_subentry is None:
        _LOGGER.warning("No Network subentry found, skipping number entity setup")
        return

    # Get the device registry
    dr = device_registry.async_get(hass)

    # Get or create the Network device (same identifier pattern as sensors)
    device_entry = dr.async_get_or_create(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_{network_subentry.subentry_id}_{NETWORK_DEVICE_NETWORK}")},
        config_entry_id=config_entry.entry_id,
        config_subentry_id=network_subentry.subentry_id,
        translation_key=NETWORK_DEVICE_NETWORK,
        translation_placeholders={"name": network_subentry.title},
    )

    # Create the blackout slack penalty number entity
    entities = [
        HaeoBlackoutSlackPenalty(
            config_entry=config_entry,
            device_entry=device_entry,
            unique_id=f"{config_entry.entry_id}_{network_subentry.subentry_id}_{NETWORK_DEVICE_NETWORK}_{BLACKOUT_SLACK_PENALTY_KEY}",
        )
    ]

    async_add_entities(entities)
    _LOGGER.debug("Created blackout slack penalty number entity for hub %s", config_entry.entry_id)


class HaeoBlackoutSlackPenalty(RestoreEntity, NumberEntity):
    """Number entity for configuring the blackout slack penalty."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = BLACKOUT_SLACK_PENALTY_KEY
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1000.0
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_entry: device_registry.DeviceEntry,
        unique_id: str,
    ) -> None:
        """Initialize the number entity."""
        self._config_entry = config_entry
        self.device_entry = device_entry
        self._attr_unique_id = unique_id
        self._attr_native_value: float = 0.2  # Default value

    async def async_added_to_hass(self) -> None:
        """Restore previous state when added to hass."""
        await super().async_added_to_hass()

        # Try to restore the previous value
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
                _LOGGER.debug("Restored blackout slack penalty value: %s", self._attr_native_value)
            except (ValueError, TypeError):
                _LOGGER.warning("Could not restore blackout slack penalty value from %s", last_state.state)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()
        _LOGGER.debug("Blackout slack penalty set to %s", value)
