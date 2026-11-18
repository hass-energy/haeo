"""Tests for the config entry version 1.7 migration."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.migrations import v1_7
from custom_components.haeo.unique_id import element_output_unique_id


def _add(hass: HomeAssistant, entry: MockConfigEntry, name: str, data: dict[str, object]) -> ConfigSubentry:
    element_type = str(data[CONF_ELEMENT_TYPE])
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_NAME: name, **data}), subentry_type=element_type, title=name, unique_id=None
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry


def _sensor(
    hass: HomeAssistant, entry: MockConfigEntry, subentry: ConfigSubentry, output: str, unit: str | None
) -> str:
    return (
        er.async_get(hass)
        .async_get_or_create(
            "sensor",
            DOMAIN,
            element_output_unique_id(entry.entry_id, subentry.subentry_id, subentry.subentry_type, output),
            config_entry=entry,
            config_subentry_id=subentry.subentry_id,
            suggested_object_id=f"{subentry.title}_{output}",
            unit_of_measurement=unit,
        )
        .entity_id
    )


async def test_buffer_names_its_loads_and_generation_by_their_power_sensors(hass: HomeAssistant) -> None:
    """Each listed element is named by its first power sensor, and one without a power sensor directly."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=6)
    entry.add_to_hass(hass)
    house = _add(hass, entry, "House", {CONF_ELEMENT_TYPE: ElementType.LOAD})
    solar = _add(hass, entry, "Solar", {CONF_ELEMENT_TYPE: ElementType.SOLAR})
    _add(hass, entry, "Pool pump", {CONF_ELEMENT_TYPE: ElementType.DEFERRABLE_LOAD})
    _sensor(hass, entry, house, "load_shadow_price", "$/kWh")
    house_power = _sensor(hass, entry, house, "load_power", UnitOfPower.KILO_WATT)
    solar_power = _sensor(hass, entry, solar, "solar_power", UnitOfPower.KILO_WATT)
    _sensor(hass, entry, solar, "solar_power_available", UnitOfPower.KILO_WATT)
    buffer = _add(
        hass,
        entry,
        "Backup",
        {
            CONF_ELEMENT_TYPE: ElementType.BUFFER,
            "kind": "reserve",
            "participants": {"loads": ["House", "Pool pump"], "generation": ["Solar"], "storage": ["Battery"]},
        },
    )

    assert await v1_7.async_migrate_entry(hass, entry)

    assert entry.minor_version == v1_7.MINOR_VERSION
    assert entry.subentries[buffer.subentry_id].data["participants"] == {
        "loads": {**as_entity_value([house_power]), "elements": ["Pool pump"]},
        "generation": as_entity_value([solar_power]),
        "storage": ["Battery"],
    }
    assert entry.subentries[house.subentry_id].data == house.data
