"""Tests for config entry migration helpers."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import migrations
from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
)
from custom_components.haeo.elements import battery, battery_section, connection, grid, inverter, load, node, solar
from custom_components.haeo.flows import (
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.migrations import async_migrate_entry, v1_3
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_EFFICIENCY,
    SECTION_FORECAST,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)


def _create_subentry(data: dict[str, Any], *, subentry_type: str | None = None) -> ConfigSubentry:
    """Create a ConfigSubentry with the given data."""
    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=subentry_type or str(data.get(CONF_ELEMENT_TYPE, "unknown")),
        title=str(data.get(CONF_NAME, "unnamed")),
        unique_id=None,
    )


def test_migrate_hub_data_moves_basic_and_builds_sections() -> None:
    """Hub migration should move basic data and build sectioned data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            "basic": {CONF_NAME: "Custom Hub"},
            CONF_HORIZON_PRESET: "custom",
            CONF_TIER_1_COUNT: 4,
            CONF_TIER_1_DURATION: 10,
        },
        options={
            CONF_DEBOUNCE_SECONDS: 12,
            CONF_ADVANCED_MODE: True,
            CONF_TIER_1_COUNT: 4,
            CONF_TIER_1_DURATION: 10,
        },
    )

    migrated_data, migrated_options = v1_3._migrate_hub_data(entry)

    assert HUB_SECTION_COMMON in migrated_data
    assert HUB_SECTION_TIERS in migrated_data
    assert HUB_SECTION_ADVANCED in migrated_data
    assert migrated_data[HUB_SECTION_COMMON][CONF_NAME] == "Test Hub"
    assert migrated_data[HUB_SECTION_COMMON][CONF_HORIZON_PRESET] == "custom"
    assert migrated_data[HUB_SECTION_TIERS][CONF_TIER_1_COUNT] == 4
    assert migrated_data[HUB_SECTION_TIERS][CONF_TIER_1_DURATION] == 10
    assert migrated_data[HUB_SECTION_ADVANCED][CONF_DEBOUNCE_SECONDS] == 12
    assert migrated_data[HUB_SECTION_ADVANCED][CONF_ADVANCED_MODE] is True
    assert CONF_NAME not in migrated_data
    assert CONF_HORIZON_PRESET not in migrated_data
    assert migrated_options == {}


def test_migrate_hub_data_skips_when_sections_present() -> None:
    """Hub migration should skip when sections already exist."""
    data = {
        HUB_SECTION_COMMON: {CONF_NAME: "Hub", CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS},
        HUB_SECTION_TIERS: {CONF_TIER_1_COUNT: 2, CONF_TIER_1_DURATION: 5},
        HUB_SECTION_ADVANCED: {CONF_DEBOUNCE_SECONDS: 30, CONF_ADVANCED_MODE: False},
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data=data, options={"keep": "value"})

    migrated_data, migrated_options = v1_3._migrate_hub_data(entry)

    assert migrated_data == data
    assert migrated_options == entry.options


@pytest.mark.parametrize("element_type", [None, ELEMENT_TYPE_NETWORK])
def test_migrate_subentry_returns_none_for_non_elements(element_type: str | None) -> None:
    """Subentry migration should skip missing or network element types."""
    data: dict[str, Any] = {}
    if element_type is not None:
        data[CONF_ELEMENT_TYPE] = element_type

    subentry = _create_subentry(data, subentry_type="network")

    assert v1_3.migrate_subentry_data(subentry) is None


def test_migrate_subentry_battery_with_legacy_fields() -> None:
    """Battery migration should map legacy fields into sections."""
    data = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
        CONF_CONNECTION: "bus",
        battery.CONF_CAPACITY: "sensor.capacity",
        battery.CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.initial",
        battery.CONF_MIN_CHARGE_PERCENTAGE: 0.1,
        battery.CONF_MAX_CHARGE_PERCENTAGE: 0.9,
        battery.CONF_EFFICIENCY_SOURCE_TARGET: 0.85,
        battery.CONF_EFFICIENCY_TARGET_SOURCE: 0.88,
        battery.CONF_CONFIGURE_PARTITIONS: True,
        "max_charge_power": 4.2,
        "max_discharge_power": 6.1,
        "discharge_cost": 0.25,
        "early_charge_incentive": 0.15,
        "efficiency": 0.92,
        SECTION_POWER_LIMITS: {CONF_MAX_POWER_SOURCE_TARGET: 7.0},
        SECTION_PRICING: {CONF_PRICE_SOURCE_TARGET: 0.33},
        battery.SECTION_UNDERCHARGE: {battery.CONF_PARTITION_PERCENTAGE: 0.1},
        battery.SECTION_OVERCHARGE: {battery.CONF_PARTITION_COST: 0.2},
    }
    subentry = _create_subentry(data, subentry_type=battery.ELEMENT_TYPE)

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    assert migrated[SECTION_COMMON][CONF_NAME] == "Battery"
    assert migrated[SECTION_COMMON][CONF_CONNECTION] == as_connection_target("bus")
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(7.0)
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(4.2)
    assert migrated[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.33)
    assert migrated[SECTION_PRICING][CONF_PRICE_TARGET_SOURCE] == as_constant_value(0.15)
    assert migrated[SECTION_EFFICIENCY][battery.CONF_EFFICIENCY_SOURCE_TARGET] == as_constant_value(0.85)
    assert migrated[SECTION_EFFICIENCY][battery.CONF_EFFICIENCY_TARGET_SOURCE] == as_constant_value(0.88)
    assert migrated[battery.SECTION_UNDERCHARGE][battery.CONF_PARTITION_PERCENTAGE] == as_constant_value(0.1)
    assert migrated[battery.SECTION_OVERCHARGE][battery.CONF_PARTITION_COST] == as_constant_value(0.2)


def test_migrate_subentry_battery_invalid_schema_value_raises() -> None:
    """Battery migration should raise for unsupported schema values."""
    data = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
        battery.CONF_CAPACITY: {"invalid": "value"},
    }
    subentry = _create_subentry(data, subentry_type=battery.ELEMENT_TYPE)

    with pytest.raises(TypeError, match="Unsupported schema value"):
        v1_3._migrate_subentry_data(subentry)


def test_migrate_subentry_battery_section() -> None:
    """Battery section migration should map storage values."""
    data = {
        CONF_ELEMENT_TYPE: battery_section.ELEMENT_TYPE,
        CONF_NAME: "Battery Section",
        battery_section.CONF_CAPACITY: 5.0,
        battery_section.CONF_INITIAL_CHARGE: 2.5,
    }
    subentry = _create_subentry(data, subentry_type=battery_section.ELEMENT_TYPE)

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    assert migrated[SECTION_COMMON][CONF_NAME] == "Battery Section"
    assert migrated[battery_section.SECTION_STORAGE][battery_section.CONF_CAPACITY] == as_constant_value(5.0)
    assert migrated[battery_section.SECTION_STORAGE][battery_section.CONF_INITIAL_CHARGE] == as_constant_value(2.5)


def test_migrate_subentry_connection_fields() -> None:
    """Connection migration should map endpoints, limits, pricing, and efficiency."""
    data = {
        CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
        CONF_NAME: "Connection",
        connection.SECTION_ENDPOINTS: {connection.CONF_SOURCE: "node_a", connection.CONF_TARGET: "node_b"},
        SECTION_POWER_LIMITS: {
            connection.CONF_MAX_POWER_SOURCE_TARGET: 4.0,
            connection.CONF_MAX_POWER_TARGET_SOURCE: 3.5,
        },
        SECTION_PRICING: {
            connection.CONF_PRICE_SOURCE_TARGET: 0.1,
            connection.CONF_PRICE_TARGET_SOURCE: 0.2,
        },
        SECTION_EFFICIENCY: {
            connection.CONF_EFFICIENCY_SOURCE_TARGET: 0.9,
            connection.CONF_EFFICIENCY_TARGET_SOURCE: 0.91,
        },
    }
    subentry = _create_subentry(data, subentry_type=connection.ELEMENT_TYPE)

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    assert migrated[SECTION_COMMON][CONF_NAME] == "Connection"
    assert migrated[connection.SECTION_ENDPOINTS][connection.CONF_SOURCE] == as_connection_target("node_a")
    assert migrated[SECTION_POWER_LIMITS][connection.CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(4.0)
    assert migrated[SECTION_PRICING][connection.CONF_PRICE_TARGET_SOURCE] == as_constant_value(0.2)
    assert migrated[SECTION_EFFICIENCY][connection.CONF_EFFICIENCY_TARGET_SOURCE] == as_constant_value(0.91)


def test_migrate_subentry_grid_legacy_fields() -> None:
    """Grid migration should map legacy import/export fields."""
    data = {
        CONF_ELEMENT_TYPE: grid.ELEMENT_TYPE,
        CONF_NAME: "Grid",
        CONF_CONNECTION: "bus",
        "import_price": 0.3,
        "export_price": 0.1,
        "import_limit": 5.0,
        "export_limit": 4.0,
    }
    subentry = _create_subentry(data, subentry_type=grid.ELEMENT_TYPE)

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    assert migrated[SECTION_COMMON][CONF_CONNECTION] == as_connection_target("bus")
    assert migrated[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.3)
    assert migrated[SECTION_PRICING][CONF_PRICE_TARGET_SOURCE] == as_constant_value(0.1)
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(5.0)
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(4.0)


def test_migrate_subentry_inverter_legacy_fields() -> None:
    """Inverter migration should map power limits and efficiency."""
    data = {
        CONF_ELEMENT_TYPE: inverter.ELEMENT_TYPE,
        CONF_NAME: "Inverter",
        CONF_CONNECTION: "bus",
        "max_power_dc_to_ac": 7.0,
        "max_power_ac_to_dc": 6.0,
        "efficiency_dc_to_ac": 0.95,
        "efficiency_ac_to_dc": 0.94,
    }
    subentry = _create_subentry(data, subentry_type=inverter.ELEMENT_TYPE)

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    assert migrated[SECTION_COMMON][CONF_NAME] == "Inverter"
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(7.0)
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(6.0)
    assert migrated[SECTION_EFFICIENCY][inverter.CONF_EFFICIENCY_SOURCE_TARGET] == as_constant_value(0.95)
    assert migrated[SECTION_EFFICIENCY][inverter.CONF_EFFICIENCY_TARGET_SOURCE] == as_constant_value(0.94)


def test_migrate_subentry_load_node_solar() -> None:
    """Load, node, and solar migrations should map sectioned fields."""
    load_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            CONF_NAME: "Load",
            CONF_CONNECTION: "bus",
            CONF_FORECAST: ["sensor.load"],
        },
        subentry_type=load.ELEMENT_TYPE,
    )
    load_migrated = v1_3.migrate_subentry_data(load_subentry)
    assert load_migrated is not None
    assert load_migrated[SECTION_COMMON][CONF_CONNECTION] == as_connection_target("bus")
    assert load_migrated[SECTION_FORECAST][CONF_FORECAST] == as_entity_value(["sensor.load"])
    assert load_migrated[SECTION_PRICING] == {}
    assert load_migrated[SECTION_CURTAILMENT] == {}

    node_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: node.ELEMENT_TYPE,
            CONF_NAME: "Node",
            node.CONF_IS_SOURCE: True,
            node.CONF_IS_SINK: False,
        },
        subentry_type=node.ELEMENT_TYPE,
    )
    node_migrated = v1_3.migrate_subentry_data(node_subentry)
    assert node_migrated is not None
    assert node_migrated[node.SECTION_ROLE][node.CONF_IS_SOURCE] is True
    assert node_migrated[node.SECTION_ROLE][node.CONF_IS_SINK] is False

    solar_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: solar.ELEMENT_TYPE,
            CONF_NAME: "Solar",
            CONF_CONNECTION: "bus",
            CONF_FORECAST: ["sensor.solar"],
            "price_production": 0.12,
            solar.CONF_CURTAILMENT: True,
        },
        subentry_type=solar.ELEMENT_TYPE,
    )
    solar_migrated = v1_3.migrate_subentry_data(solar_subentry)
    assert solar_migrated is not None
    assert solar_migrated[SECTION_COMMON][CONF_CONNECTION] == as_connection_target("bus")
    assert solar_migrated[SECTION_FORECAST][CONF_FORECAST] == as_entity_value(["sensor.solar"])
    assert solar_migrated[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.12)
    assert solar_migrated[solar.SECTION_CURTAILMENT][solar.CONF_CURTAILMENT] == as_constant_value(True)


def test_migrate_subentry_load_maps_legacy_shedding() -> None:
    """Load migration should map legacy shedding -> curtailment."""
    load_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            CONF_NAME: "Load",
            CONF_CONNECTION: "bus",
            CONF_FORECAST: ["sensor.load"],
            "shedding": {"shedding": True},
        },
        subentry_type=load.ELEMENT_TYPE,
    )
    migrated = v1_3._migrate_subentry_data(load_subentry)
    assert migrated is not None
    assert migrated[SECTION_CURTAILMENT][CONF_CURTAILMENT] == as_constant_value(True)


async def test_async_migrate_entry_updates_entry_and_subentries(hass: HomeAssistant) -> None:
    """async_migrate_entry should update entry data and subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hub",
        data={
            CONF_NAME: "Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS,
            CONF_TIER_1_COUNT: 1,
            CONF_TIER_1_DURATION: 5,
        },
        options={CONF_ADVANCED_MODE: True},
    )
    entry.add_to_hass(hass)

    subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: grid.ELEMENT_TYPE,
            CONF_NAME: "Grid",
            CONF_CONNECTION: "bus",
            "import_price": 0.3,
        },
        subentry_type=grid.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    result = await v1_3.async_migrate_entry(hass, entry)

    assert result is True
    assert entry.minor_version == v1_3.MINOR_VERSION
    assert HUB_SECTION_COMMON in entry.data
    assert entry.options == {}
    migrated_subentry = next(iter(entry.subentries.values()))
    assert SECTION_PRICING in migrated_subentry.data


async def test_async_migrate_entry_skips_when_up_to_date(hass: HomeAssistant) -> None:
    """async_migrate_entry should return True when already at target version."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=v1_3.MINOR_VERSION)

    result = await v1_3.async_migrate_entry(hass, entry)

    assert result is True
    assert entry.minor_version == v1_3.MINOR_VERSION


async def test_migrations_entry_skips_non_v1(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Migration dispatcher should skip non-v1 entries."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, version=2)

    async_handler = AsyncMock(return_value=True)
    monkeypatch.setattr(migrations, "MIGRATIONS", ((1, async_handler),))

    result = await async_migrate_entry(hass, entry)

    assert result is True
    async_handler.assert_not_awaited()


async def test_migrations_entry_runs_handlers(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Migration dispatcher should invoke registered handlers."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=0)

    async_handler = AsyncMock(return_value=True)
    monkeypatch.setattr(migrations, "MIGRATIONS", ((1, async_handler),))

    result = await async_migrate_entry(hass, entry)

    assert result is True
    async_handler.assert_awaited_once_with(hass, entry)
