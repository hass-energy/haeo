"""Migration for config entry version 1.6.

Gives every EV a public charging price. The price is no longer optional, as it
also values the energy left in the pack at the horizon end, so an EV saved
without one gets the default as a constant.
"""

from __future__ import annotations

from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.core.schema import as_constant_value, is_none_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import (
    CONF_PUBLIC_CHARGING_PRICE,
    DEFAULT_PUBLIC_CHARGING_PRICE,
    SECTION_PUBLIC_CHARGING,
)
from custom_components.haeo.core.schema.migrations import section_dict

MINOR_VERSION: Final = 6


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set the default public charging price on every EV saved without one."""
    for subentry in list(entry.subentries.values()):
        if subentry.subentry_type != ElementType.EV:
            continue
        public_charging = section_dict(subentry.data, SECTION_PUBLIC_CHARGING)
        price = public_charging.get(CONF_PUBLIC_CHARGING_PRICE)
        if price is not None and not is_none_value(price):
            continue
        public_charging[CONF_PUBLIC_CHARGING_PRICE] = as_constant_value(DEFAULT_PUBLIC_CHARGING_PRICE)
        hass.config_entries.async_update_subentry(
            entry, subentry, data={**subentry.data, SECTION_PUBLIC_CHARGING: public_charging}
        )

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    return True
