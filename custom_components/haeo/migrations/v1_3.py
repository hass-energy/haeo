"""Migration helpers for config entry version 1.3."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
)
from custom_components.haeo.flows import (
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 3


def _migrate_hub_data(entry: ConfigEntry) -> tuple[dict[str, Any], dict[str, Any]]:
    """Migrate hub entry data/options into sectioned config data."""
    data = dict(entry.data)
    options = dict(entry.options)

    if "basic" in data and HUB_SECTION_COMMON not in data:
        data[HUB_SECTION_COMMON] = data.pop("basic")

    if HUB_SECTION_COMMON in data and HUB_SECTION_ADVANCED in data and HUB_SECTION_TIERS in data:
        return data, options

    horizon_preset = options.get(CONF_HORIZON_PRESET) or data.get(CONF_HORIZON_PRESET) or HORIZON_PRESET_5_DAYS
    tiers = {
        CONF_TIER_1_COUNT: options.get(CONF_TIER_1_COUNT, DEFAULT_TIER_1_COUNT),
        CONF_TIER_1_DURATION: options.get(CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION),
        CONF_TIER_2_COUNT: options.get(CONF_TIER_2_COUNT, DEFAULT_TIER_2_COUNT),
        CONF_TIER_2_DURATION: options.get(CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION),
        CONF_TIER_3_COUNT: options.get(CONF_TIER_3_COUNT, DEFAULT_TIER_3_COUNT),
        CONF_TIER_3_DURATION: options.get(CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION),
        CONF_TIER_4_COUNT: options.get(CONF_TIER_4_COUNT, DEFAULT_TIER_4_COUNT),
        CONF_TIER_4_DURATION: options.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION),
    }
    advanced = {
        CONF_DEBOUNCE_SECONDS: options.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS),
        CONF_ADVANCED_MODE: options.get(CONF_ADVANCED_MODE, False),
    }

    data[HUB_SECTION_COMMON] = {CONF_NAME: data.get(CONF_NAME, entry.title), CONF_HORIZON_PRESET: horizon_preset}
    data[HUB_SECTION_TIERS] = tiers
    data[HUB_SECTION_ADVANCED] = advanced

    for key in (
        CONF_NAME,
        CONF_HORIZON_PRESET,
        CONF_ADVANCED_MODE,
        CONF_DEBOUNCE_SECONDS,
        CONF_TIER_1_COUNT,
        CONF_TIER_1_DURATION,
        CONF_TIER_2_COUNT,
        CONF_TIER_2_DURATION,
        CONF_TIER_3_COUNT,
        CONF_TIER_3_DURATION,
        CONF_TIER_4_COUNT,
        CONF_TIER_4_DURATION,
    ):
        data.pop(key, None)

    return data, {}


def migrate_subentry_data(subentry: ConfigSubentry) -> dict[str, Any] | None:
    """Migrate a subentry's data to sectioned config if needed."""
    from custom_components.haeo.core.migrations.v1_3 import migrate_element_config  # noqa: PLC0415

    return migrate_element_config(dict(subentry.data))


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.3."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    new_data, new_options = _migrate_hub_data(entry)
    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        options=new_options,
        minor_version=MINOR_VERSION,
    )

    for subentry in entry.subentries.values():
        migrated = migrate_subentry_data(subentry)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
