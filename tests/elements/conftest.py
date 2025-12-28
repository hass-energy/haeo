"""Shared fixtures for element tests."""

from types import MappingProxyType
from typing import Any

import pytest
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPES, ElementType


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a minimal hub entry for flow testing.

    Only includes fields required for element flow tests. Tier configuration
    and other hub-specific settings are not needed for testing element flows.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_ADVANCED_MODE: True,  # Enable advanced mode for all element types
        },
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)
    return entry


def create_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, element_type: ElementType) -> Any:
    """Create a configured subentry flow instance for an element type."""
    registry_entry = ELEMENT_TYPES[element_type]
    flow_class = registry_entry.flow_class
    flow = flow_class()
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, element_type)
    return flow


def add_participant(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    name: str,
    element_type: str = "node",
) -> ConfigSubentry:
    """Add a participant subentry for connection endpoints."""
    data = MappingProxyType({CONF_ELEMENT_TYPE: element_type, CONF_NAME: name})
    subentry = ConfigSubentry(
        data=data,
        subentry_type=element_type,
        title=name,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry
