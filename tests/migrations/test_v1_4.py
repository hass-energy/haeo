"""Tests for config entry migration helpers in v1.4."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, DOMAIN
from custom_components.haeo.elements import load, solar
from custom_components.haeo.migrations import v1_4
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value, is_schema_value
from custom_components.haeo.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_PRICING,
)


def _create_subentry(data: dict[str, Any], *, subentry_type: str | None = None) -> ConfigSubentry:
    """Create a ConfigSubentry with the given data."""
    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=subentry_type or str(data.get(CONF_ELEMENT_TYPE, "unknown")),
        title="subentry",
        unique_id=None,
    )


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        pytest.param(as_constant_value(True), "schema", id="schema_value_passthrough"),
        pytest.param(True, "schema", id="bool_to_schema"),
        pytest.param(1.25, "schema", id="number_to_schema"),
        pytest.param("sensor.foo", "schema", id="str_to_schema_entity"),
        pytest.param(["sensor.a", "sensor.b"], "schema", id="list_str_to_schema_entity"),
        pytest.param({"unsupported": "value"}, "raw", id="unsupported_passthrough"),
    ],
)
def test_to_schema_value_converts_supported_types(value: object, expected_type: str) -> None:
    """_to_schema_value should convert primitives and pass through unsupported."""
    converted = v1_4._to_schema_value(value)
    if expected_type == "schema":
        assert is_schema_value(converted)
    else:
        assert converted == value


def test_migrate_subentry_load_adds_sections_and_maps_legacy_shedding() -> None:
    """Load migration should add pricing/curtailment and map legacy shedding -> curtailment."""
    subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            SECTION_COMMON: {CONF_CONNECTION: as_connection_target("bus"), "name": "Load"},
            # Legacy section name and field name.
            "shedding": {"shedding": True},
        },
        subentry_type=load.ELEMENT_TYPE,
    )

    migrated = v1_4._migrate_subentry_data(subentry)
    assert migrated is not None
    assert SECTION_PRICING in migrated
    assert migrated[SECTION_PRICING] == {}
    assert migrated[SECTION_CURTAILMENT][CONF_CURTAILMENT] == as_constant_value(True)


def test_migrate_subentry_load_does_not_override_existing_curtailment() -> None:
    """Load migration should not overwrite an existing curtailment value."""
    subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            SECTION_COMMON: {CONF_CONNECTION: as_connection_target("bus"), "name": "Load"},
            SECTION_PRICING: {},
            SECTION_CURTAILMENT: {CONF_CURTAILMENT: as_constant_value(value=False)},
            "shedding": {"shedding": True},
        },
        subentry_type=load.ELEMENT_TYPE,
    )

    migrated = v1_4._migrate_subentry_data(subentry)
    assert migrated is not None
    assert migrated[SECTION_CURTAILMENT][CONF_CURTAILMENT] == as_constant_value(value=False)


def test_migrate_subentry_load_converts_legacy_shedding_strings() -> None:
    """Load migration should convert legacy shedding strings into entity schema values."""
    subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            SECTION_COMMON: {CONF_CONNECTION: as_connection_target("bus"), "name": "Load"},
            "shedding": {"shedding": "binary_sensor.shedding_enabled"},
        },
        subentry_type=load.ELEMENT_TYPE,
    )

    migrated = v1_4._migrate_subentry_data(subentry)
    assert migrated is not None
    assert migrated[SECTION_CURTAILMENT][CONF_CURTAILMENT] == as_entity_value(["binary_sensor.shedding_enabled"])


def test_migrate_subentry_solar_backfills_sections() -> None:
    """Solar migration should ensure pricing and curtailment sections exist."""
    subentry = _create_subentry({CONF_ELEMENT_TYPE: solar.ELEMENT_TYPE}, subentry_type=solar.ELEMENT_TYPE)

    migrated = v1_4._migrate_subentry_data(subentry)
    assert migrated is not None
    assert migrated[SECTION_PRICING] == {}
    assert migrated[SECTION_CURTAILMENT] == {}


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({}, id="missing_element_type"),
        pytest.param({CONF_ELEMENT_TYPE: 123}, id="non_str_element_type"),
        pytest.param({CONF_ELEMENT_TYPE: "unknown"}, id="unknown_element_type"),
    ],
)
def test_migrate_subentry_returns_none_for_non_matching(data: dict[str, Any]) -> None:
    """Migration should return None for non-element/unknown data."""
    subentry = _create_subentry(data)
    assert v1_4._migrate_subentry_data(subentry) is None


async def test_async_migrate_entry_updates_minor_and_subentries(hass: HomeAssistant) -> None:
    """async_migrate_entry should update entry minor version and subentries in place."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    load_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            SECTION_COMMON: {"name": "Load", CONF_CONNECTION: as_connection_target("bus")},
            "shedding": {"shedding": False},
        },
        subentry_type=load.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, load_subentry)

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == v1_4.MINOR_VERSION

    migrated_subentry = next(iter(entry.subentries.values()))
    assert SECTION_PRICING in migrated_subentry.data
    assert SECTION_CURTAILMENT in migrated_subentry.data


async def test_async_migrate_entry_skips_non_v1(hass: HomeAssistant) -> None:
    """async_migrate_entry should skip non-v1 entries."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={}, version=2, minor_version=0)
    entry.add_to_hass(hass)

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == 0


async def test_async_migrate_entry_skips_when_up_to_date(hass: HomeAssistant) -> None:
    """async_migrate_entry should do nothing when already at or above target minor."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={}, version=1, minor_version=v1_4.MINOR_VERSION)
    entry.add_to_hass(hass)

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == v1_4.MINOR_VERSION
