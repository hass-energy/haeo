"""Tests for network connectivity helpers."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DOMAIN,
)
from custom_components.haeo.coordinator import evaluate_network_connectivity
from custom_components.haeo.elements import ELEMENT_TYPE_CONNECTION, ELEMENT_TYPE_NODE, ElementConfigData
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET, SECTION_ENDPOINTS, ConnectionConfigData
from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, NodeConfigData
from custom_components.haeo.sections import SECTION_ADVANCED, SECTION_COMMON, SECTION_POWER_LIMITS, SECTION_PRICING


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a configured HAEO hub entry for network tests."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "common": {CONF_NAME: "Test Hub"},
            "tiers": {
                CONF_TIER_1_COUNT: 2,
                CONF_TIER_1_DURATION: 30,
                CONF_TIER_2_COUNT: 0,
                CONF_TIER_2_DURATION: 60,
                CONF_TIER_3_COUNT: 0,
                CONF_TIER_3_DURATION: 30,
                CONF_TIER_4_COUNT: 0,
                CONF_TIER_4_DURATION: 60,
            },
            "advanced": {},
        },
        entry_id="test_entry",
        title="Test Hub",
    )
    entry.add_to_hass(hass)
    return entry


async def test_evaluate_network_connectivity_connected(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Network with a single node should be considered connected."""

    node_a: NodeConfigData = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
        SECTION_COMMON: {CONF_NAME: "Node A"},
        SECTION_ADVANCED: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    participants: dict[str, ElementConfigData] = {"Node A": node_a}

    await evaluate_network_connectivity(hass, config_entry, participants=participants)

    issue_id = f"disconnected_network_{config_entry.entry_id}"
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is None


async def test_evaluate_network_connectivity_disconnected(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Network with isolated nodes should create a repair issue."""

    node_a: NodeConfigData = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
        SECTION_COMMON: {CONF_NAME: "Node A"},
        SECTION_ADVANCED: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    node_b: NodeConfigData = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
        SECTION_COMMON: {CONF_NAME: "Node B"},
        SECTION_ADVANCED: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    participants: dict[str, ElementConfigData] = {"Node A": node_a, "Node B": node_b}

    await evaluate_network_connectivity(hass, config_entry, participants=participants)

    issue_id = f"disconnected_network_{config_entry.entry_id}"
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == "disconnected_network"


async def test_evaluate_network_connectivity_resolves_issue(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Validation should clear the issue when connectivity is restored."""

    node_a: NodeConfigData = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
        SECTION_COMMON: {CONF_NAME: "Node A"},
        SECTION_ADVANCED: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    node_b: NodeConfigData = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
        SECTION_COMMON: {CONF_NAME: "Node B"},
        SECTION_ADVANCED: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    participants: dict[str, ElementConfigData] = {"Node A": node_a, "Node B": node_b}

    await evaluate_network_connectivity(hass, config_entry, participants=participants)

    # Connect the nodes and re-validate
    connection: ConnectionConfigData = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION,
        SECTION_COMMON: {
            CONF_NAME: "A to B",
        },
        SECTION_ENDPOINTS: {
            CONF_SOURCE: "Node A",
            CONF_TARGET: "Node B",
        },
        SECTION_POWER_LIMITS: {},
        SECTION_PRICING: {},
        SECTION_ADVANCED: {},
    }
    participants["A to B"] = connection

    await evaluate_network_connectivity(hass, config_entry, participants=participants)

    issue_id = f"disconnected_network_{config_entry.entry_id}"
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is None
