"""Tests for inverter element config flow."""

from collections.abc import Generator
from types import MappingProxyType
from unittest.mock import MagicMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, HAEO_CONFIGURABLE_UNIQUE_ID
from custom_components.haeo.elements import node
from custom_components.haeo.elements.inverter import (
    CONF_CONNECTION,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
    ELEMENT_TYPE,
)

from ..conftest import add_participant, create_flow

# Test entity ID for the configurable entity
TEST_CONFIGURABLE_ENTITY_ID = "haeo.configurable_entity"


@pytest.fixture
def mock_configurable_entity() -> Generator[None]:
    """Mock the entity registry to recognize the configurable test entity."""
    mock_entry = MagicMock()
    mock_entry.unique_id = HAEO_CONFIGURABLE_UNIQUE_ID

    def mock_async_get(entity_id: str) -> MagicMock | None:
        if entity_id == TEST_CONFIGURABLE_ENTITY_ID:
            return mock_entry
        return None

    mock_registry = MagicMock()
    mock_registry.async_get = mock_async_get
    mock_registry.async_get_entity_id.return_value = TEST_CONFIGURABLE_ENTITY_ID

    with patch("custom_components.haeo.flows.field_schema.er.async_get", return_value=mock_registry):
        yield


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Inverter reconfigure should include deleted connection target in options."""
    # Create inverter that references a deleted connection target
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "DeletedNode",  # This node no longer exists
        CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_to_ac"],
        CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_to_dc"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
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


# --- Tests for validation errors ---


async def test_user_step_empty_required_fields_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Submitting step 1 with empty required fields should show errors."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit with empty required fields
    user_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [],
        CONF_MAX_POWER_AC_TO_DC: [],
    }
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    errors = result.get("errors", {})
    assert CONF_MAX_POWER_DC_TO_AC in errors
    assert CONF_MAX_POWER_AC_TO_DC in errors


# --- Tests for two-step flow with configurable values ---


async def test_user_step_with_configurable_shows_values_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Selecting configurable entity should show values form (step 2)."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit step 1 with configurable entities selected
    step1_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_MAX_POWER_AC_TO_DC: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_user(user_input=step1_input)

    # Should show values form (step 2)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"


async def test_values_step_creates_entry_with_constant(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Submitting values step should create entry with constant values."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Inverter",
            "data": {},
        }
    )

    # Step 1: select configurable entities
    step1_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_MAX_POWER_AC_TO_DC: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_user(user_input=step1_input)
    assert result.get("step_id") == "values"

    # Step 2: provide constant values
    step2_input = {
        CONF_MAX_POWER_DC_TO_AC: 5.0,
        CONF_MAX_POWER_AC_TO_DC: 5.0,
    }
    result = await flow.async_step_values(user_input=step2_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][CONF_MAX_POWER_DC_TO_AC] == 5.0
    assert create_kwargs["data"][CONF_MAX_POWER_AC_TO_DC] == 5.0


async def test_values_step_missing_required_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Submitting values step with missing required configurable value should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Step 1: select configurable entities
    step1_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_MAX_POWER_AC_TO_DC: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_user(user_input=step1_input)
    assert result.get("step_id") == "values"

    # Step 2: submit without providing one of the required values
    step2_input = {
        CONF_MAX_POWER_AC_TO_DC: 5.0,
    }
    result = await flow.async_step_values(user_input=step2_input)

    # Should show values form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"
    assert CONF_MAX_POWER_DC_TO_AC in result.get("errors", {})


# --- Tests for reconfigure flow ---


async def test_reconfigure_empty_required_fields_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Reconfigure with empty required fields should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_to_ac"],
        CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_to_dc"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Submit with empty required fields
    step1_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [],
        CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_to_dc"],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)

    # Should show reconfigure form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"
    assert CONF_MAX_POWER_DC_TO_AC in result.get("errors", {})


async def test_reconfigure_with_configurable_shows_values_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Reconfigure with configurable entity should show values form."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_to_ac"],
        CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_to_dc"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Step 1: change to configurable entities
    step1_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_MAX_POWER_AC_TO_DC: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)

    # Should show values form (step 2)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure_values"


async def test_reconfigure_values_step_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Submitting reconfigure values step should update entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_to_ac"],
        CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_to_dc"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # Step 1: change to configurable entities
    step1_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_MAX_POWER_AC_TO_DC: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)
    assert result.get("step_id") == "reconfigure_values"

    # Step 2: provide constant values
    step2_input = {
        CONF_MAX_POWER_DC_TO_AC: 10.0,
        CONF_MAX_POWER_AC_TO_DC: 10.0,
    }
    result = await flow.async_step_reconfigure_values(user_input=step2_input)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config contains the constant values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][CONF_MAX_POWER_DC_TO_AC] == 10.0
    assert update_kwargs["data"][CONF_MAX_POWER_AC_TO_DC] == 10.0


async def test_reconfigure_values_step_missing_required_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    mock_configurable_entity: None,
) -> None:
    """Reconfigure values step with missing required configurable value should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_to_ac"],
        CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_to_dc"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Step 1: change to configurable entities
    step1_input = {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        CONF_MAX_POWER_DC_TO_AC: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_MAX_POWER_AC_TO_DC: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)
    assert result.get("step_id") == "reconfigure_values"

    # Step 2: submit without providing one of the required values
    step2_input = {
        CONF_MAX_POWER_AC_TO_DC: 10.0,
    }
    result = await flow.async_step_reconfigure_values(user_input=step2_input)

    # Should show reconfigure_values form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure_values"
    assert CONF_MAX_POWER_DC_TO_AC in result.get("errors", {})
