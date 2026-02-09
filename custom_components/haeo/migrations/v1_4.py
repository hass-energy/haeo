"""Migration helpers for config entry version 1.4.

Ensures newer required sections/fields exist for existing subentries:
- Load: add `pricing` and `curtailment` sections (and migrate legacy `shedding`)
- Solar: ensure `pricing` and `curtailment` sections exist
"""

from __future__ import annotations

import logging
from numbers import Real
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import CONF_ELEMENT_TYPE, DOMAIN
from custom_components.haeo.elements import load, solar
from custom_components.haeo.schema import (
    as_constant_value,
    as_entity_value,
    is_schema_value,
)
from custom_components.haeo.sections import (
    CONF_CURTAILMENT,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_CURTAILMENT,
    SECTION_PRICING,
)

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4


def _to_schema_value(value: object) -> object:
    """Convert legacy primitive values to schema values when needed."""
    if is_schema_value(value):
        return value
    if isinstance(value, bool):
        return as_constant_value(value)
    if isinstance(value, Real):
        return as_constant_value(float(value))
    if isinstance(value, str):
        return as_entity_value([value])
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return as_entity_value(value)
    return value


def _migrate_subentry_data(subentry: ConfigSubentry) -> dict[str, Any] | None:
    """Migrate a subentry's data if required."""
    data = dict(subentry.data)
    element_type = data.get(CONF_ELEMENT_TYPE)
    if not isinstance(element_type, str):
        return None

    migrated: dict[str, Any] = dict(data)

    if element_type == load.ELEMENT_TYPE:
        # Ensure pricing section exists (default: disabled).
        migrated.setdefault(SECTION_PRICING, {})

        # Handle legacy section name "shedding" and field name "shedding".
        legacy_shedding_section = migrated.pop("shedding", None)
        curtailment_section = migrated.get(SECTION_CURTAILMENT)

        if not isinstance(curtailment_section, dict):
            curtailment_section = {}

        if isinstance(legacy_shedding_section, dict) and CONF_CURTAILMENT not in curtailment_section:
            if "shedding" in legacy_shedding_section:
                curtailment_section[CONF_CURTAILMENT] = _to_schema_value(legacy_shedding_section["shedding"])

        migrated[SECTION_CURTAILMENT] = curtailment_section
        return migrated

    if element_type == solar.ELEMENT_TYPE:
        migrated.setdefault(SECTION_PRICING, {})
        migrated.setdefault(SECTION_CURTAILMENT, {})
        return migrated

    return None


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.4."""
    if entry.version != 1:
        return True

    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)

    for subentry in entry.subentries.values():
        migrated = _migrate_subentry_data(subentry)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True

