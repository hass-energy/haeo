"""Tests for config entry migration helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import migrations
from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
)
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import (
    battery,
    battery_section,
    connection,
    grid,
    inverter,
    load,
    node,
    solar,
)
from custom_components.haeo.core.schema.elements.policy import CONF_RULES
from custom_components.haeo.core.schema.migrations import v1_3 as schema_migrations
from custom_components.haeo.core.schema.migrations.v1_3 import ElementMigrationStep, migrate_hub_config
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_CURTAILMENT,
    SECTION_EFFICIENCY,
    SECTION_FORECAST,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.flows import (
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.migrations import async_migrate_entry, v1_3

V033_SCENARIO_FIXTURES_DIR = Path(__file__).parent / "test_data" / "v0_3_3" / "scenarios"


def _load_v033_scenario_config(name: str) -> dict[str, Any]:
    """Load a v0.3.3 scenario config fixture."""
    with (V033_SCENARIO_FIXTURES_DIR / f"{name}_config.json").open() as fixture:
        return json.load(fixture)  # type: ignore[no-any-return]


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
    data: dict[str, Any] = {
        "basic": {CONF_NAME: "Custom Hub"},
        CONF_HORIZON_PRESET: "custom",
        CONF_TIER_1_COUNT: 4,
        CONF_TIER_1_DURATION: 10,
    }
    options: dict[str, Any] = {
        CONF_DEBOUNCE_SECONDS: 12,
        CONF_ADVANCED_MODE: True,
        CONF_TIER_1_COUNT: 4,
        CONF_TIER_1_DURATION: 10,
    }

    migrated_data, migrated_options = migrate_hub_config(data, options, "Test Hub")

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
    data: dict[str, Any] = {
        HUB_SECTION_COMMON: {CONF_NAME: "Hub", CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS},
        HUB_SECTION_TIERS: {CONF_TIER_1_COUNT: 2, CONF_TIER_1_DURATION: 5},
        HUB_SECTION_ADVANCED: {CONF_DEBOUNCE_SECONDS: 30, CONF_ADVANCED_MODE: False},
    }
    options: dict[str, Any] = {"keep": "value"}

    migrated_data, migrated_options = migrate_hub_config(data, options, "Hub")

    assert migrated_data == data
    assert migrated_options == options


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
    assert migrated[CONF_NAME] == "Battery"
    assert migrated[CONF_CONNECTION] == as_connection_target("bus")
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(7.0)
    assert migrated[SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(4.2)
    assert migrated[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.33)
    assert migrated[SECTION_PRICING][CONF_PRICE_TARGET_SOURCE] == as_constant_value(0.15)
    assert migrated[SECTION_EFFICIENCY][battery.CONF_EFFICIENCY_SOURCE_TARGET] == as_constant_value(0.85)
    assert migrated[SECTION_EFFICIENCY][battery.CONF_EFFICIENCY_TARGET_SOURCE] == as_constant_value(0.88)
    assert migrated[battery.SECTION_UNDERCHARGE][battery.CONF_PARTITION_PERCENTAGE] == as_constant_value(0.1)
    assert migrated[battery.SECTION_OVERCHARGE][battery.CONF_PARTITION_COST] == as_constant_value(0.2)


def test_migrate_subentry_battery_without_salvage_value_stays_valid() -> None:
    """Migrated legacy battery without salvage_value still validates."""
    data = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
        CONF_CONNECTION: "bus",
        battery.CONF_CAPACITY: "sensor.capacity",
        battery.CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.initial",
        "early_charge_incentive": 0.15,
    }
    subentry = _create_subentry(data, subentry_type=battery.ELEMENT_TYPE)

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    pricing = migrated[SECTION_PRICING]
    assert isinstance(pricing, dict)
    assert battery.CONF_SALVAGE_VALUE not in pricing
    assert is_element_config_schema(migrated) is True


def test_migrate_subentry_battery_invalid_schema_value_raises() -> None:
    """Battery migration should raise for unsupported schema values."""
    data = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
        battery.CONF_CAPACITY: {"invalid": "value"},
    }
    subentry = _create_subentry(data, subentry_type=battery.ELEMENT_TYPE)

    with pytest.raises(TypeError, match="Unsupported schema value"):
        v1_3.migrate_subentry_data(subentry)


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
    assert migrated[CONF_NAME] == "Battery Section"
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
    assert migrated[CONF_NAME] == "Connection"
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
    assert migrated[CONF_CONNECTION] == as_connection_target("bus")
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
    assert migrated[CONF_NAME] == "Inverter"
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
    assert load_migrated[CONF_CONNECTION] == as_connection_target("bus")
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
    assert solar_migrated[CONF_CONNECTION] == as_connection_target("bus")
    assert solar_migrated[SECTION_FORECAST][CONF_FORECAST] == as_entity_value(["sensor.solar"])
    assert solar_migrated[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.12)
    assert solar_migrated[solar.SECTION_CURTAILMENT][solar.CONF_CURTAILMENT] == as_constant_value(True)


@pytest.mark.parametrize(
    ("element_type", "legacy_data"),
    [
        pytest.param(
            battery.ELEMENT_TYPE,
            {
                CONF_NAME: "Battery",
                CONF_CONNECTION: "main",
                battery.CONF_CAPACITY: "sensor.battery_capacity",
                battery.CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
                "max_charge_power": 4.0,
                "max_discharge_power": 5.0,
                "early_charge_incentive": 0.01,
            },
            id="battery-flat-v033",
        ),
        pytest.param(
            battery_section.ELEMENT_TYPE,
            {
                CONF_NAME: "Battery section",
                battery_section.CONF_CAPACITY: 5.0,
                battery_section.CONF_INITIAL_CHARGE: 2.0,
            },
            id="battery-section-flat-v033",
        ),
        pytest.param(
            connection.ELEMENT_TYPE,
            {
                CONF_NAME: "Connection",
                connection.CONF_SOURCE: "node_a",
                connection.CONF_TARGET: "node_b",
                connection.CONF_MAX_POWER_SOURCE_TARGET: 4.0,
                connection.CONF_MAX_POWER_TARGET_SOURCE: 4.0,
                connection.CONF_PRICE_SOURCE_TARGET: 0.1,
                connection.CONF_PRICE_TARGET_SOURCE: 0.2,
            },
            id="connection-flat-v033",
        ),
        pytest.param(
            grid.ELEMENT_TYPE,
            {
                CONF_NAME: "Grid",
                CONF_CONNECTION: "main",
                "import_price": 0.3,
                "export_price": 0.1,
                "import_limit": 6.0,
                "export_limit": 5.0,
            },
            id="grid-flat-v033",
        ),
        pytest.param(
            inverter.ELEMENT_TYPE,
            {
                CONF_NAME: "Inverter",
                CONF_CONNECTION: "main",
                "max_power_dc_to_ac": 8.0,
                "max_power_ac_to_dc": 6.0,
                "efficiency_dc_to_ac": 0.95,
                "efficiency_ac_to_dc": 0.94,
            },
            id="inverter-flat-v033",
        ),
        pytest.param(
            load.ELEMENT_TYPE,
            {
                CONF_NAME: "Load",
                CONF_CONNECTION: "main",
                CONF_FORECAST: ["sensor.load_forecast"],
                "shedding": {"shedding": True},
            },
            id="load-flat-v033",
        ),
        pytest.param(
            node.ELEMENT_TYPE,
            {
                CONF_NAME: "Node",
                node.CONF_IS_SOURCE: True,
                node.CONF_IS_SINK: False,
            },
            id="node-flat-v033",
        ),
        pytest.param(
            solar.ELEMENT_TYPE,
            {
                CONF_NAME: "Solar",
                CONF_CONNECTION: "main",
                CONF_FORECAST: ["sensor.solar_forecast"],
                "price_production": 0.0,
                solar.CONF_CURTAILMENT: False,
            },
            id="solar-flat-v033",
        ),
    ],
)
def test_migrate_subentry_v033_legacy_shape_is_schema_valid(
    element_type: str,
    legacy_data: dict[str, Any],
) -> None:
    """v0.3.3-style flat subentry data migrates to valid main-branch schema."""
    subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: element_type,
            **legacy_data,
        },
        subentry_type=element_type,
    )

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    assert is_element_config_schema(migrated) is True


@pytest.mark.parametrize(
    "scenario_name",
    [
        pytest.param("scenario1", id="scenario1"),
        pytest.param("scenario2", id="scenario2"),
        pytest.param("scenario3", id="scenario3"),
        pytest.param("scenario4", id="scenario4"),
        pytest.param("scenario5", id="scenario5"),
    ],
)
def test_migrate_v033_scenario_configs_to_current_schema(scenario_name: str) -> None:
    """v0.3.3 scenario fixtures migrate end-to-end to current schema shapes."""
    legacy_config = _load_v033_scenario_config(scenario_name)
    participants = legacy_config["participants"]
    assert isinstance(participants, dict)

    legacy_hub = dict(legacy_config)
    del legacy_hub["participants"]

    migrated_hub, migrated_options = migrate_hub_config(legacy_hub, {}, f"Scenario {scenario_name}")

    assert HUB_SECTION_COMMON in migrated_hub
    assert HUB_SECTION_TIERS in migrated_hub
    assert HUB_SECTION_ADVANCED in migrated_hub
    assert migrated_options == {}

    migrated_participants: dict[str, dict[str, Any]] = {}
    for participant_name, participant_data in participants.items():
        assert isinstance(participant_name, str)
        assert isinstance(participant_data, dict)
        migrated = v1_3.migrate_subentry_data(_create_subentry(participant_data))
        assert migrated is not None
        assert is_element_config_schema(migrated) is True
        migrated_participants[participant_name] = migrated

    assert set(migrated_participants) == set(participants)
    battery_pricing = migrated_participants["Battery"][SECTION_PRICING]
    assert isinstance(battery_pricing, dict)
    assert battery.CONF_SALVAGE_VALUE not in battery_pricing


def test_migrate_element_config_short_circuits_when_step_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Migration pipeline returns None when an intermediate step drops config."""
    steps = (
        ElementMigrationStep(
            name="drop_all",
            transform=lambda _data: None,
        ),
        ElementMigrationStep(
            name="should_not_run",
            transform=lambda data: dict(data),
        ),
    )
    monkeypatch.setattr(schema_migrations, "ELEMENT_MIGRATION_STEPS", steps)

    migrated = schema_migrations.migrate_element_config(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Battery",
        }
    )

    assert migrated is None


def test_migrate_element_config_returns_copy_when_no_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline returns a fresh dict unchanged when no steps are configured."""
    monkeypatch.setattr(schema_migrations, "ELEMENT_MIGRATION_STEPS", ())
    original = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
    }

    migrated = schema_migrations.migrate_element_config(original)

    assert migrated == original
    assert migrated is not original


@pytest.mark.parametrize(
    ("element_type", "extra_data"),
    [
        (grid.ELEMENT_TYPE, {"import_price": 0.3}),
        (inverter.ELEMENT_TYPE, {"max_power_dc_to_ac": 7.0}),
        (load.ELEMENT_TYPE, {CONF_FORECAST: ["sensor.load"]}),
        (solar.ELEMENT_TYPE, {CONF_FORECAST: ["sensor.solar"]}),
    ],
)
def test_migrate_subentry_without_connection(element_type: str, extra_data: dict[str, Any]) -> None:
    """Elements without a connection should migrate without normalize_connection_target."""
    data: dict[str, Any] = {CONF_ELEMENT_TYPE: element_type, CONF_NAME: "Test", **extra_data}
    subentry = _create_subentry(data, subentry_type=element_type)

    migrated = v1_3.migrate_subentry_data(subentry)

    assert migrated is not None
    assert migrated[CONF_NAME] == "Test"
    assert CONF_CONNECTION not in migrated


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
    migrated = v1_3.migrate_subentry_data(load_subentry)
    assert migrated is not None
    assert migrated[SECTION_CURTAILMENT][CONF_CURTAILMENT] == as_constant_value(True)


def test_extract_pricing_rules_ignores_non_pricing_elements() -> None:
    """Pricing rule extraction skips element types other than battery and solar."""
    subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            CONF_NAME: "Load",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: {"type": "constant", "value": 0.2},
            },
        },
        subentry_type=load.ELEMENT_TYPE,
    )

    rules = v1_3._extract_pricing_rules(dict(subentry.data), subentry)
    assert rules == []


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


async def test_async_migrate_entry_migrates_battery_pricing_to_policy_rules(hass: HomeAssistant) -> None:
    """v1.3 migration creates policy rules from battery pricing."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    battery_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: {"type": "constant", "value": 0.04},
                CONF_PRICE_TARGET_SOURCE: {"type": "constant", "value": 0.02},
            },
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == v1_3.MINOR_VERSION

    policy_subentry = next(s for s in entry.subentries.values() if s.subentry_type == "policy")
    rules = policy_subentry.data[CONF_RULES]
    assert len(rules) == 2
    assert {rule["name"] for rule in rules} == {"Bat Discharge", "Bat Charge"}


async def test_async_migrate_entry_normalizes_unique_ids(hass: HomeAssistant) -> None:
    """v1.3 migration normalizes section-prefixed unique IDs."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)

    old_entry = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_bat001_storage.capacity",
        config_entry=entry,
    )

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True

    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_storage.capacity") is None
    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_capacity") == old_entry.entity_id


async def test_async_migrate_entry_deduplicates_unique_id_conflicts(hass: HomeAssistant) -> None:
    """v1.3 migration removes section-prefixed duplicates when stable ID exists."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)

    stable_entry = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_bat001_capacity",
        config_entry=entry,
    )
    duplicate_entry = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_bat001_storage.capacity",
        config_entry=entry,
    )

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True
    assert registry.async_get(stable_entry.entity_id) is not None
    assert registry.async_get(duplicate_entry.entity_id) is None


async def test_async_migrate_entry_handles_non_constant_charge_price(hass: HomeAssistant) -> None:
    """Non-constant charge price keeps value and logs migration warning."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    battery_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: {"type": "entity", "value": ["sensor.price"]},
            },
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    result = await v1_3.async_migrate_entry(hass, entry)

    assert result is True
    policy_subentry = next(s for s in entry.subentries.values() if s.subentry_type == "policy")
    rules = policy_subentry.data[CONF_RULES]
    assert len(rules) == 1
    assert rules[0]["name"] == "Bat Charge"
    assert rules[0]["price"] == {"type": "entity", "value": ["sensor.price"]}


@pytest.mark.parametrize(
    ("element_type", "field_name", "value"),
    [
        pytest.param("battery", CONF_PRICE_SOURCE_TARGET, 0.0, id="battery-discharge-default"),
        pytest.param("battery", CONF_PRICE_TARGET_SOURCE, 0.0, id="battery-charge-zero-default"),
        pytest.param("battery", CONF_PRICE_TARGET_SOURCE, 0.01, id="battery-charge-legacy-default"),
        pytest.param("solar", CONF_PRICE_SOURCE_TARGET, 0.0, id="solar-production-default"),
    ],
)
def test_is_default_policy_price_matches_known_defaults(element_type: str, field_name: str, value: float) -> None:
    """Default pricing constants are recognized and skipped by migration."""
    assert v1_3._is_default_policy_price(element_type, field_name, {"type": "constant", "value": value}) is True


def test_is_default_policy_price_ignores_non_default_or_non_constant_values() -> None:
    """Only exact configured default constants are treated as defaults."""
    assert (
        v1_3._is_default_policy_price(
            "battery",
            CONF_PRICE_TARGET_SOURCE,
            {"type": "constant", "value": 0.02},
        )
        is False
    )
    assert (
        v1_3._is_default_policy_price(
            "battery",
            CONF_PRICE_TARGET_SOURCE,
            {"type": "entity", "value": ["sensor.price"]},
        )
        is False
    )
    assert (
        v1_3._is_default_policy_price(
            "unknown",
            CONF_PRICE_TARGET_SOURCE,
            {"type": "constant", "value": 0.01},
        )
        is False
    )
    assert (
        v1_3._is_default_policy_price(
            "battery",
            CONF_PRICE_TARGET_SOURCE,
            {"type": "constant", "value": "0.01"},
        )
        is False
    )


async def test_async_migrate_entry_skips_default_policy_prices(hass: HomeAssistant) -> None:
    """Default legacy pricing values do not produce migrated policy rules."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    battery_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: {"type": "constant", "value": 0.0},
                CONF_PRICE_TARGET_SOURCE: {"type": "constant", "value": 0.01},
            },
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    solar_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: solar.ELEMENT_TYPE,
            CONF_NAME: "PV",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: {"type": "constant", "value": 0.0},
            },
        },
        subentry_type=solar.ELEMENT_TYPE,
    )

    hass.config_entries.async_add_subentry(entry, battery_subentry)
    hass.config_entries.async_add_subentry(entry, solar_subentry)

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True
    assert all(s.subentry_type != "policy" for s in entry.subentries.values())


async def test_async_migrate_entry_handles_non_mapping_battery_pricing(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-mapping pricing values are treated as empty without creating policy rules."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    battery_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: "not-a-dict",
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    monkeypatch.setattr(v1_3, "migrate_subentry_data", lambda subentry: dict(subentry.data))

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True
    assert all(s.subentry_type != "policy" for s in entry.subentries.values())


async def test_async_migrate_entry_merges_into_existing_policy_and_strips_pricing(hass: HomeAssistant) -> None:
    """Solar/load/battery pricing handling merges into existing policy subentry."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    existing_policy = _create_subentry(
        {
            CONF_ELEMENT_TYPE: "policy",
            CONF_NAME: "Policies",
            CONF_RULES: [
                {
                    "name": "Existing Rule",
                    "enabled": True,
                    "source": ["Grid"],
                    "target": ["Load"],
                    "price": {"type": "constant", "value": 0.11},
                }
            ],
        },
        subentry_type="policy",
    )
    solar_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: solar.ELEMENT_TYPE,
            CONF_NAME: "PV",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: {"type": "constant", "value": 0.03},
            },
        },
        subentry_type=solar.ELEMENT_TYPE,
    )
    battery_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: "not-a-dict",
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    load_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
            CONF_NAME: "Load",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: {"type": "constant", "value": 0.2},
            },
        },
        subentry_type=load.ELEMENT_TYPE,
    )
    connection_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
            CONF_NAME: "Line",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: {"type": "constant", "value": 0.1},
            },
        },
        subentry_type=connection.ELEMENT_TYPE,
    )

    hass.config_entries.async_add_subentry(entry, existing_policy)
    hass.config_entries.async_add_subentry(entry, solar_subentry)
    hass.config_entries.async_add_subentry(entry, battery_subentry)
    hass.config_entries.async_add_subentry(entry, load_subentry)
    hass.config_entries.async_add_subentry(entry, connection_subentry)

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True

    updated_policy = next(s for s in entry.subentries.values() if s.subentry_type == "policy")
    rules = updated_policy.data[CONF_RULES]
    assert len(rules) == 2
    assert rules[0]["name"] == "Existing Rule"
    assert rules[1]["name"] == "PV Production"

    updated_solar = next(s for s in entry.subentries.values() if s.subentry_type == solar.ELEMENT_TYPE)
    assert SECTION_PRICING not in updated_solar.data

    updated_battery = next(s for s in entry.subentries.values() if s.subentry_type == battery.ELEMENT_TYPE)
    assert updated_battery.data[SECTION_PRICING] == {}

    updated_load = next(s for s in entry.subentries.values() if s.subentry_type == load.ELEMENT_TYPE)
    assert SECTION_PRICING not in updated_load.data

    updated_connection = next(s for s in entry.subentries.values() if s.subentry_type == connection.ELEMENT_TYPE)
    assert updated_connection.data[SECTION_PRICING] == {
        CONF_PRICE_SOURCE_TARGET: {"type": "constant", "value": 0.1},
    }


async def test_async_migrate_entry_skips_solar_rule_without_price(hass: HomeAssistant) -> None:
    """Solar entry without source-target price does not create a policy rule."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    solar_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: solar.ELEMENT_TYPE,
            CONF_NAME: "PV",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {},
        },
        subentry_type=solar.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, solar_subentry)

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True
    assert all(s.subentry_type != "policy" for s in entry.subentries.values())


async def test_async_migrate_entry_unique_id_callback_edge_cases(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unique-ID migration handles malformed, empty, and list-item identifiers."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)

    class DummyRegistryEntry:
        def __init__(self, unique_id: str, entity_id: str) -> None:
            self.unique_id = unique_id
            self.entity_id = entity_id
            self.domain = "number"
            self.platform = DOMAIN

    async def fake_migrate_entries(
        _hass: HomeAssistant,
        _entry_id: str,
        entry_callback: Any,
    ) -> None:
        assert entry_callback(DummyRegistryEntry("", "number.empty")) is None
        assert entry_callback(DummyRegistryEntry("invalid", "number.invalid")) is None
        assert entry_callback(DummyRegistryEntry("entry_sub_rules.0.price", "number.rules")) is None

        migrated = entry_callback(DummyRegistryEntry("entry_sub_storage.capacity", "number.capacity"))
        assert migrated == {"new_unique_id": "entry_sub_capacity"}

    monkeypatch.setattr(v1_3.er, "async_migrate_entries", fake_migrate_entries)

    result = await v1_3.async_migrate_entry(hass, entry)
    assert result is True


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
