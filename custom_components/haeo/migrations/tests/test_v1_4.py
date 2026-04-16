"""Tests for config entry migration to version 1.4 (policy subentries)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import as_constant_value
from custom_components.haeo.core.schema.elements import battery, solar
from custom_components.haeo.core.schema.elements.policy import CONF_RULES
from custom_components.haeo.core.schema.none_value import as_none_value
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_PRICING,
)
from custom_components.haeo.migrations import v1_3, v1_4


def _create_subentry(data: dict[str, Any], *, subentry_type: str | None = None) -> ConfigSubentry:
    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=subentry_type or str(data.get(CONF_ELEMENT_TYPE, "unknown")),
        title=str(data.get(CONF_NAME, "unnamed")),
        unique_id=None,
    )


@pytest.mark.asyncio
async def test_v1_4_migrates_battery_pricing_to_policy_rules(hass: HomeAssistant) -> None:
    """Battery discharge and charge prices become policy subentries with rules[]."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=v1_3.MINOR_VERSION)

    bat = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.04),
                CONF_PRICE_TARGET_SOURCE: as_constant_value(0.01),
            },
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, bat)

    assert await v1_4.async_migrate_entry(hass, entry) is True

    assert entry.minor_version == v1_4.MINOR_VERSION
    policy_subs = [s for s in entry.subentries.values() if s.subentry_type == "policy"]
    assert len(policy_subs) == 2
    titles = {s.title for s in policy_subs}
    assert "Bat Discharge Cost" in titles
    assert "Bat Charge Incentive" in titles
    for sub in policy_subs:
        assert CONF_RULES in sub.data
        assert len(sub.data[CONF_RULES]) == 1
        assert "price" in sub.data[CONF_RULES][0]

    updated_bat = next(s for s in entry.subentries.values() if s.subentry_type == battery.ELEMENT_TYPE)
    pricing = dict(updated_bat.data.get(SECTION_PRICING, {}))
    assert CONF_PRICE_SOURCE_TARGET not in pricing
    assert CONF_PRICE_TARGET_SOURCE not in pricing


@pytest.mark.asyncio
async def test_v1_4_migrates_legacy_battery_discharge_cost_to_policy(hass: HomeAssistant) -> None:
    """Pre-sectioned battery with only discharge_cost still becomes a discharge policy."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=v1_3.MINOR_VERSION)

    bat = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            "discharge_cost": as_constant_value(0.12),
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, bat)

    assert await v1_4.async_migrate_entry(hass, entry) is True

    policy_subs = [s for s in entry.subentries.values() if s.subentry_type == "policy"]
    assert len(policy_subs) == 1
    assert policy_subs[0].title == "Bat Discharge Cost"
    assert policy_subs[0].data[CONF_RULES][0]["source"] == ["Bat"]

    updated_bat = next(s for s in entry.subentries.values() if s.subentry_type == battery.ELEMENT_TYPE)
    assert "discharge_cost" not in updated_bat.data


@pytest.mark.asyncio
async def test_v1_4_migrates_solar_pricing_to_policy_rules(hass: HomeAssistant) -> None:
    """Solar production price becomes one policy subentry with one rule."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=v1_3.MINOR_VERSION)

    pv = _create_subentry(
        {
            CONF_ELEMENT_TYPE: solar.ELEMENT_TYPE,
            CONF_NAME: "PV",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.03),
            },
        },
        subentry_type=solar.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, pv)

    assert await v1_4.async_migrate_entry(hass, entry) is True

    policy_subs = [s for s in entry.subentries.values() if s.subentry_type == "policy"]
    assert len(policy_subs) == 1
    assert policy_subs[0].title == "PV Production Cost"
    rule = policy_subs[0].data[CONF_RULES][0]
    assert rule["source"] == ["PV"]

    updated_solar = next(s for s in entry.subentries.values() if s.subentry_type == solar.ELEMENT_TYPE)
    assert SECTION_PRICING not in updated_solar.data


@pytest.mark.asyncio
async def test_v1_4_no_op_when_already_current(hass: HomeAssistant) -> None:
    """Migration short-circuits when the entry is already at minor version 1.4."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=v1_4.MINOR_VERSION)

    assert await v1_4.async_migrate_entry(hass, entry) is True


@pytest.mark.asyncio
async def test_v1_4_battery_discharge_falls_back_past_explicit_none_price(hass: HomeAssistant) -> None:
    """Discharge price that is explicitly none still allows legacy discharge_cost to migrate."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=v1_3.MINOR_VERSION)

    bat = _create_subentry(
        {
            CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
            CONF_NAME: "Bat",
            CONF_CONNECTION: "bus",
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_none_value(),
            },
            "discharge_cost": as_constant_value(0.08),
        },
        subentry_type=battery.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, bat)

    assert await v1_4.async_migrate_entry(hass, entry) is True

    policy_subs = [s for s in entry.subentries.values() if s.subentry_type == "policy"]
    assert len(policy_subs) == 1
    assert policy_subs[0].data[CONF_RULES][0]["price"] == as_constant_value(0.08)


@pytest.mark.asyncio
async def test_v1_4_battery_ignores_non_mapping_pricing_section(hass: HomeAssistant) -> None:
    """Malformed pricing data is treated as empty; legacy keys can still migrate."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"})
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=v1_3.MINOR_VERSION)

    malformed_battery: dict[str, Any] = {
        CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
        CONF_NAME: "Bat",
        CONF_CONNECTION: "bus",
        SECTION_PRICING: "not-a-mapping",
        "discharge_cost": as_constant_value(0.11),
    }
    bat = _create_subentry(malformed_battery, subentry_type=battery.ELEMENT_TYPE)
    hass.config_entries.async_add_subentry(entry, bat)

    assert await v1_4.async_migrate_entry(hass, entry) is True

    policy_subs = [s for s in entry.subentries.values() if s.subentry_type == "policy"]
    assert len(policy_subs) == 1
    assert policy_subs[0].data[CONF_RULES][0]["price"] == as_constant_value(0.11)
