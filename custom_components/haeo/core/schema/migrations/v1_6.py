"""Pure config transformation logic for the v1.6 migration.

Every EV gets a public charging price. The price is no longer optional, as it
also values the energy left in the pack at the horizon end, so an EV saved
without one gets the default as a constant.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import as_constant_value, is_none_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import (
    CONF_PUBLIC_CHARGING_PRICE,
    DEFAULT_PUBLIC_CHARGING_PRICE,
    SECTION_PUBLIC_CHARGING,
)
from custom_components.haeo.core.schema.migrations import section_dict

# The config entry minor version these migrations bring an entry to
MINOR_VERSION: Final = 6


def migrate_element_config(config: Mapping[str, object]) -> dict[str, object] | None:
    """Return an EV config given the default public charging price, or None when the config needs no change."""
    if config.get(CONF_ELEMENT_TYPE) != ElementType.EV:
        return None
    public_charging = section_dict(config, SECTION_PUBLIC_CHARGING)
    price = public_charging.get(CONF_PUBLIC_CHARGING_PRICE)
    if price is not None and not is_none_value(price):
        return None
    public_charging[CONF_PUBLIC_CHARGING_PRICE] = as_constant_value(DEFAULT_PUBLIC_CHARGING_PRICE)
    return {**config, SECTION_PUBLIC_CHARGING: public_charging}
