"""Tests that a config entry saved by HAEO 0.4 upgrades and sets up."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, ELEMENT_TYPE_NETWORK, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
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
    HORIZON_PRESET_2_DAYS,
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import battery, buffer, connection, grid, junction, node
from custom_components.haeo.core.schema.elements.conformance import is_element_config_schema
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

SOURCE_NODE = "Generator bus"

# Element configs as HAEO 0.4 stored them
LEGACY_ELEMENTS: tuple[dict[str, object], ...] = (
    {CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK, CONF_NAME: "System"},
    {
        CONF_ELEMENT_TYPE: node.ELEMENT_TYPE,
        CONF_NAME: "Switchboard",
        node.SECTION_ROLE: {node.CONF_IS_SOURCE: False, node.CONF_IS_SINK: False},
    },
    {
        CONF_ELEMENT_TYPE: node.ELEMENT_TYPE,
        CONF_NAME: SOURCE_NODE,
        node.SECTION_ROLE: {node.CONF_IS_SOURCE: True, node.CONF_IS_SINK: False},
    },
    {
        CONF_ELEMENT_TYPE: grid.ELEMENT_TYPE,
        CONF_NAME: "Grid",
        CONF_CONNECTION: as_connection_target("Switchboard"),
        SECTION_PRICING: {
            CONF_PRICE_SOURCE_TARGET: as_constant_value(0.3),
            CONF_PRICE_TARGET_SOURCE: as_constant_value(0.05),
        },
        SECTION_POWER_LIMITS: {},
    },
    {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Battery",
        CONF_CONNECTION: as_connection_target("Switchboard"),
        battery.SECTION_STORAGE: {
            battery.CONF_CAPACITY: as_constant_value(10.0),
            battery.CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
        },
        battery.SECTION_LIMITS: {
            battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(10.0),
            battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(90.0),
        },
        SECTION_POWER_LIMITS: {},
        SECTION_PRICING: {battery.CONF_SALVAGE_VALUE: as_constant_value(0.0)},
        SECTION_EFFICIENCY: {},
        partitions.SECTION_PARTITIONING: {partitions.CONF_CONFIGURE_PARTITIONS: True},
        partitions.SECTION_UNDERCHARGE: {
            partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(5.0),
            partitions.CONF_PARTITION_COST: as_constant_value(0.03),
        },
        partitions.SECTION_OVERCHARGE: {
            partitions.CONF_PARTITION_PERCENTAGE: as_constant_value(95.0),
            partitions.CONF_PARTITION_COST: as_constant_value(0.04),
        },
    },
    {
        CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
        CONF_NAME: "Generator link",
        connection.SECTION_ENDPOINTS: {
            connection.CONF_SOURCE: as_connection_target(SOURCE_NODE),
            connection.CONF_TARGET: as_connection_target("Switchboard"),
        },
        SECTION_POWER_LIMITS: {
            CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(3.0),
        },
        SECTION_PRICING: {CONF_PRICE_TARGET_SOURCE: as_constant_value(0.01)},
        SECTION_EFFICIENCY: {
            CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(98.0),
            CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
        },
        "segment_order": {"mirror_segment_order": True},
    },
)

CUSTOM_TIERS = {
    CONF_TIER_1_COUNT: 10,
    CONF_TIER_1_DURATION: 1,
    CONF_TIER_2_COUNT: 20,
    CONF_TIER_2_DURATION: 5,
    CONF_TIER_3_COUNT: 40,
    CONF_TIER_3_DURATION: 30,
    CONF_TIER_4_COUNT: 24,
    CONF_TIER_4_DURATION: 60,
}


def _legacy_hub(hass: HomeAssistant, *, preset: str, advanced_mode: bool) -> MockConfigEntry:
    """Add a hub as HAEO 0.4 stored it, with every legacy element."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Home", CONF_HORIZON_PRESET: preset},
            HUB_SECTION_TIERS: CUSTOM_TIERS,
            HUB_SECTION_ADVANCED: {CONF_DEBOUNCE_SECONDS: 2, CONF_ADVANCED_MODE: advanced_mode},
        },
        version=1,
        minor_version=3,
    )
    entry.add_to_hass(hass)
    for data in LEGACY_ELEMENTS:
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType(data),
                subentry_type=str(data[CONF_ELEMENT_TYPE]),
                title=str(data[CONF_NAME]),
                unique_id=None,
            ),
        )
    return entry


@pytest.mark.parametrize(
    ("preset", "advanced_mode", "expected_preset"),
    [
        pytest.param(HORIZON_PRESET_5_DAYS, False, HORIZON_PRESET_5_DAYS, id="5_days"),
        pytest.param("custom", False, HORIZON_PRESET_5_DAYS, id="custom"),
        pytest.param(HORIZON_PRESET_2_DAYS, True, HORIZON_PRESET_2_DAYS, id="2_days_advanced"),
    ],
)
async def test_hub_from_0_4_upgrades_and_sets_up(
    hass: HomeAssistant, preset: str, advanced_mode: bool, expected_preset: str
) -> None:
    """A hub saved by HAEO 0.4 migrates to the current config and sets up with every element valid."""
    entry = _legacy_hub(hass, preset=preset, advanced_mode=advanced_mode)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.minor_version == 4
    assert entry.data[HUB_SECTION_COMMON][CONF_HORIZON] == as_horizon_preset_value(expected_preset)
    subentries = {subentry.title: subentry for subentry in entry.subentries.values()}
    assert all(
        is_element_config_schema(dict(subentry.data))
        for subentry in subentries.values()
        if subentry.subentry_type != ELEMENT_TYPE_NETWORK
    )
    assert subentries["Switchboard"].subentry_type == junction.ELEMENT_TYPE
    assert subentries[SOURCE_NODE].subentry_type == (node.ELEMENT_TYPE if advanced_mode else junction.ELEMENT_TYPE)
    assert subentries["Battery reserve"].subentry_type == buffer.ELEMENT_TYPE
    assert subentries["Battery headroom"].subentry_type == buffer.ELEMENT_TYPE
    reverse = subentries[f"Generator link (Switchboard to {SOURCE_NODE})"]
    assert reverse.data[SECTION_POWER_LIMITS] == {CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(3.0)}
    issues = ir.async_get(hass)
    junction_issue = issues.async_get_issue(DOMAIN, f"node_replaced_by_junction_{entry.entry_id}_{SOURCE_NODE}")
    assert (junction_issue is not None) is not advanced_mode
    horizon_issue = issues.async_get_issue(DOMAIN, f"horizon_tiers_replaced_{entry.entry_id}")
    assert (horizon_issue is not None) is (preset == "custom")

    assert await hass.config_entries.async_unload(entry.entry_id)
