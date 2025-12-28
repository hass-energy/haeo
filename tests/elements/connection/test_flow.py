"""Tests for connection element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPES, battery, grid, node
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET, ELEMENT_TYPE


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a configured hub entry for flow testing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)
    return entry


def _create_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> Any:
    """Create a configured subentry flow instance for connection."""
    registry_entry = ELEMENT_TYPES[ELEMENT_TYPE]
    flow_class = registry_entry.flow_class
    flow = flow_class()
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, ELEMENT_TYPE)
    return flow


def _add_participant(
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


async def test_flow_source_equals_target_error(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Connection flow should error when source equals target."""
    _add_participant(hass, hub_entry, "Node1", node.ELEMENT_TYPE)

    flow = _create_flow(hass, hub_entry)

    # Submit with source == target
    result = await flow.async_step_user(
        user_input={
            CONF_NAME: "Test Connection",
            CONF_SOURCE: "Node1",
            CONF_TARGET: "Node1",
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_TARGET: "cannot_connect_to_self"}


async def test_reconfigure_source_equals_target_error(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Connection reconfigure should error when source equals target."""
    _add_participant(hass, hub_entry, "Battery1", battery.ELEMENT_TYPE)
    _add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Existing Connection",
        CONF_SOURCE: "Battery1",
        CONF_TARGET: "Grid1",
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Existing Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = _create_flow(hass, hub_entry)
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Submit with source == target
    result = await flow.async_step_reconfigure(
        user_input={
            CONF_NAME: "Existing Connection",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Battery1",
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_TARGET: "cannot_connect_to_self"}


async def test_reconfigure_with_deleted_participant(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Connection reconfigure should include deleted participant in options."""
    # Add only one participant (the target)
    _add_participant(hass, hub_entry, "Grid1", grid.ELEMENT_TYPE)

    # Create connection that references a deleted source
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Old Connection",
        CONF_SOURCE: "DeletedBattery",  # This element no longer exists
        CONF_TARGET: "Grid1",
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Old Connection",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = _create_flow(hass, hub_entry)
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - should not error
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"
    # The form should be shown without errors


async def test_get_participant_names_skips_unknown_element_types(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """_get_participant_names should skip subentries with unknown element types."""
    # Add a valid participant
    _add_participant(hass, hub_entry, "ValidNode", node.ELEMENT_TYPE)

    # Add a subentry with unknown element type
    unknown_data = MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"})
    unknown_subentry = ConfigSubentry(
        data=unknown_data,
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    flow = _create_flow(hass, hub_entry)

    # Get participant names - should only include ValidNode
    participants = flow._get_participant_names()

    assert "ValidNode" in participants
    assert "Unknown" not in participants


async def test_get_current_subentry_id_returns_none_for_user_flow(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """_get_current_subentry_id should return None during user flow (not reconfigure)."""
    flow = _create_flow(hass, hub_entry)

    # During user flow, _get_reconfigure_subentry will raise
    subentry_id = flow._get_current_subentry_id()

    assert subentry_id is None
