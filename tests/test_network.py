"""Tests for network connectivity helpers."""

from typing import Any
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
from custom_components.haeo.elements import ELEMENT_TYPE_CONNECTION, ELEMENT_TYPE_NODE
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET
from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a configured HAEO hub entry for network tests."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: 2,
            CONF_TIER_1_DURATION: 30,
            CONF_TIER_2_COUNT: 0,
            CONF_TIER_2_DURATION: 60,
            CONF_TIER_3_COUNT: 0,
            CONF_TIER_3_DURATION: 30,
            CONF_TIER_4_COUNT: 0,
            CONF_TIER_4_DURATION: 60,
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

    participants: dict[str, dict[str, Any]] = {
        "Node A": {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
            CONF_NAME: "Node A",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        }
    }

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

    participants: dict[str, dict[str, Any]] = {
        "Node A": {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
            CONF_NAME: "Node A",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "Node B": {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
            CONF_NAME: "Node B",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
    }

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

    participants: dict[str, dict[str, Any]] = {
        "Node A": {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
            CONF_NAME: "Node A",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
        "Node B": {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
            CONF_NAME: "Node B",
            CONF_IS_SOURCE: False,
            CONF_IS_SINK: False,
        },
    }

    await evaluate_network_connectivity(hass, config_entry, participants=participants)

    # Connect the nodes and re-validate
    participants["A to B"] = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION,
        CONF_NAME: "A to B",
        CONF_SOURCE: "Node A",
        CONF_TARGET: "Node B",
    }

    await evaluate_network_connectivity(hass, config_entry, participants=participants)

    issue_id = f"disconnected_network_{config_entry.entry_id}"
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is None
