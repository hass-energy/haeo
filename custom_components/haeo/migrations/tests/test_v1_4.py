"""Tests for v1.4 config-entry migration (load threshold-price section)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.core.schema.elements import grid, load
from custom_components.haeo.core.schema.migrations.v1_4 import migrate_element_config
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_THRESHOLD_PRICE,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_THRESHOLD,
)
from custom_components.haeo.migrations import v1_4


def _create_subentry(data: dict[str, Any], *, subentry_type: str | None = None) -> ConfigSubentry:
    """Create a ConfigSubentry with the given data."""
    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=subentry_type or str(data.get(CONF_ELEMENT_TYPE, "unknown")),
        title=str(data.get(CONF_NAME, "unnamed")),
        unique_id=None,
    )


def _v1_3_load_subentry_without_threshold() -> dict[str, Any]:
    """Build a typical v1.3 load subentry that has no threshold section yet."""
    return {
        CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
        CONF_NAME: "Baseload",
        CONF_CONNECTION: {"type": "device", "device_type": "node", "device_id": "main_bus"},
        SECTION_FORECAST: {CONF_FORECAST: as_constant_value(2.5)},
        SECTION_CURTAILMENT: {CONF_CURTAILMENT: as_constant_value(False)},
    }


def test_migrate_load_adds_threshold_section_with_zero_default() -> None:
    """A pre-v1.4 load config without a threshold section gains one with price=0."""
    migrated = migrate_element_config(_v1_3_load_subentry_without_threshold())

    assert migrated is not None
    assert SECTION_THRESHOLD in migrated
    assert migrated[SECTION_THRESHOLD][CONF_THRESHOLD_PRICE] == as_constant_value(0.0)


def test_migrate_load_preserves_existing_threshold_value() -> None:
    """An existing threshold price is left untouched."""
    data = _v1_3_load_subentry_without_threshold()
    data[SECTION_THRESHOLD] = {CONF_THRESHOLD_PRICE: as_constant_value(0.30)}

    migrated = migrate_element_config(data)

    assert migrated is not None
    assert migrated[SECTION_THRESHOLD][CONF_THRESHOLD_PRICE] == as_constant_value(0.30)


def test_migrate_non_load_element_unchanged() -> None:
    """Non-load element configs pass through without a threshold section."""
    grid_data = {
        CONF_ELEMENT_TYPE: grid.ELEMENT_TYPE,
        CONF_NAME: "Grid",
    }
    migrated = migrate_element_config(grid_data)

    assert migrated is not None
    assert SECTION_THRESHOLD not in migrated
    assert migrated[CONF_ELEMENT_TYPE] == grid.ELEMENT_TYPE


async def test_async_migrate_entry_short_circuits_when_already_at_target_version(hass: HomeAssistant) -> None:
    """An entry already at minor_version 4 is not re-migrated."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hub",
        data={CONF_NAME: "Hub"},
        version=1,
        minor_version=v1_4.MINOR_VERSION,
    )
    entry.add_to_hass(hass)

    result = await v1_4.async_migrate_entry(hass, entry)

    assert result is True
    assert entry.minor_version == v1_4.MINOR_VERSION


async def test_async_migrate_entry_fills_missing_threshold_on_loads(hass: HomeAssistant) -> None:
    """async_migrate_entry inserts the threshold section into existing load subentries."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=3)
    entry.add_to_hass(hass)

    load_subentry = _create_subentry(
        _v1_3_load_subentry_without_threshold(),
        subentry_type=load.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, load_subentry)

    grid_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: grid.ELEMENT_TYPE,
            CONF_NAME: "Grid",
            CONF_CONNECTION: {"type": "device", "device_type": "node", "device_id": "main_bus"},
        },
        subentry_type=grid.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, grid_subentry)

    result = await v1_4.async_migrate_entry(hass, entry)

    assert result is True
    assert entry.minor_version == v1_4.MINOR_VERSION

    migrated_load = next(s for s in entry.subentries.values() if s.subentry_type == load.ELEMENT_TYPE)
    assert SECTION_THRESHOLD in migrated_load.data
    assert migrated_load.data[SECTION_THRESHOLD][CONF_THRESHOLD_PRICE] == as_constant_value(0.0)

    migrated_grid = next(s for s in entry.subentries.values() if s.subentry_type == grid.ELEMENT_TYPE)
    assert SECTION_THRESHOLD not in migrated_grid.data
