"""Migration for config entry version 1.7.

Names each buffer's loads and generation by one of their sensors, through the
pure transformation in the core schema migrations. An element's sensor is the
first of its power sensors by unique ID, which is its main power output. An
element with no registered sensor stays named directly.
"""

from __future__ import annotations

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.migrations import v1_7
from custom_components.haeo.core.schema.migrations.v1_7 import MINOR_VERSION

__all__ = ["MINOR_VERSION", "async_migrate_entry"]


def _element_sensors(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """Return each element's main power sensor, by element name."""
    titles = {subentry.subentry_id: subentry.title for subentry in entry.subentries.values()}
    sensors: dict[str, str] = {}
    power_sensors = sorted(
        (
            entity
            for entity in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
            if entity.domain == SENSOR_DOMAIN
            and entity.unit_of_measurement == UnitOfPower.KILO_WATT
            and entity.config_subentry_id in titles
        ),
        key=lambda entity: entity.unique_id,
    )
    for entity in power_sensors:
        sensors.setdefault(titles[entity.config_subentry_id or ""], entity.entity_id)
    return sensors


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Name every buffer's loads and generation by their sensors."""
    sensors = _element_sensors(hass, entry)
    for subentry in list(entry.subentries.values()):
        migrated = v1_7.migrate_element_config({CONF_ELEMENT_TYPE: subentry.subentry_type, **subentry.data}, sensors)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    return True
