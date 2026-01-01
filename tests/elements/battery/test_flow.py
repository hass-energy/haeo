"""Tests for battery element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import node
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    ELEMENT_TYPE,
)
from custom_components.haeo.flows.field_schema import MODE_SUFFIX, InputMode

from ..conftest import add_participant, create_flow


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Battery reconfigure should include deleted connection target in options."""
    # Create battery that references a deleted connection target
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "DeletedNode",  # This node no longer exists
        CONF_CAPACITY: ["sensor.capacity"],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.initial"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - should not error
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"


async def test_get_participant_names_skips_unknown_element_types(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_participant_names should skip subentries with unknown element types."""
    # Add a valid participant
    add_participant(hass, hub_entry, "ValidNode", node.ELEMENT_TYPE)

    # Add a subentry with unknown element type
    unknown_data = MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"})
    unknown_subentry = ConfigSubentry(
        data=unknown_data,
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Get participant names - should only include ValidNode
    participants = flow._get_participant_names()

    assert "ValidNode" in participants
    assert "Unknown" not in participants


async def test_get_current_subentry_id_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_current_subentry_id should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # During user flow, _get_reconfigure_subentry will raise
    subentry_id = flow._get_current_subentry_id()

    assert subentry_id is None


async def test_schema_rejects_empty_capacity_list(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Step 2 schema validation should reject empty capacity entity list."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Complete step 1 with ENTITY_LINK mode for capacity
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "TestNode",
        f"{CONF_CAPACITY}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
        f"{CONF_INITIAL_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.CONSTANT,
    }
    result = await flow.async_step_user(user_input=step1_input)

    # Should proceed to values step
    assert result.get("step_id") == "values"
    schema = result.get("data_schema")

    # Attempt to validate input with empty capacity list in step 2
    with pytest.raises(vol.MultipleInvalid) as exc_info:
        schema(
            {
                CONF_CAPACITY: [],
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
            }
        )

    assert CONF_CAPACITY in str(exc_info.value)


async def test_schema_rejects_empty_initial_charge_list(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Step 2 schema validation should reject empty initial charge percentage entity list."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Complete step 1 with ENTITY_LINK mode for initial_charge_percentage
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "TestNode",
        f"{CONF_CAPACITY}{MODE_SUFFIX}": InputMode.CONSTANT,
        f"{CONF_INITIAL_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
    }
    result = await flow.async_step_user(user_input=step1_input)

    # Should proceed to values step
    assert result.get("step_id") == "values"
    schema = result.get("data_schema")

    # Attempt to validate input with empty initial charge list in step 2
    with pytest.raises(vol.MultipleInvalid) as exc_info:
        schema(
            {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: [],
            }
        )

    assert CONF_INITIAL_CHARGE_PERCENTAGE in str(exc_info.value)
