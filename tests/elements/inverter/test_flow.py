"""Tests for inverter element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.elements import node
from custom_components.haeo.elements.inverter import (
    CONF_CONNECTION,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
    CONF_SECTION_ADVANCED,
    CONF_SECTION_BASIC,
    CONF_SECTION_LIMITS,
    ELEMENT_TYPE,
)

from ..conftest import add_participant, create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat inverter input values into sectioned config."""
    if CONF_SECTION_BASIC in flat:
        return dict(flat)
    basic = {
        CONF_NAME: flat[CONF_NAME],
        CONF_CONNECTION: flat[CONF_CONNECTION],
    }
    limits = {
        CONF_MAX_POWER_DC_TO_AC: flat[CONF_MAX_POWER_DC_TO_AC],
        CONF_MAX_POWER_AC_TO_DC: flat[CONF_MAX_POWER_AC_TO_DC],
    }
    return {
        CONF_SECTION_BASIC: basic,
        CONF_SECTION_LIMITS: limits,
        CONF_SECTION_ADVANCED: {},
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat inverter config values into sectioned config with element type."""
    if CONF_SECTION_BASIC in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **_wrap_input(flat)}


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Inverter reconfigure should include deleted connection target in options."""
    # Create inverter that references a deleted connection target
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "DeletedNode",  # This node no longer exists
            CONF_MAX_POWER_DC_TO_AC: 10.0,
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - should not error
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


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


async def test_user_step_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with empty required choose field should show required error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit with empty max_power_dc_to_ac (required field) - entity choice with empty list
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: [],
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_MAX_POWER_DC_TO_AC in result.get("errors", {})


# --- Tests for single-step flow with choose selector ---


async def test_user_step_with_constant_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with constant values should create entry directly."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Inverter",
            "data": {},
        }
    )

    # Submit with constant values using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: 10.0,
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == 10.0
    assert create_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == 8.0


async def test_user_step_with_entity_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with entity selections should create entry with entity IDs."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Inverter",
            "data": {},
        }
    )

    # Submit with entity selections
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.dc_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_power"],
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity IDs as strings (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == "sensor.dc_power"
    assert create_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == "sensor.ac_power"


# --- Tests for reconfigure flow ---


async def test_reconfigure_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with empty required field should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: "sensor.dc_power",
            CONF_MAX_POWER_AC_TO_DC: "sensor.ac_power",
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Submit with empty max_power_dc_to_ac (required field)
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: [],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.ac_power"],
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    # Should show reconfigure form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_MAX_POWER_DC_TO_AC in result.get("errors", {})


async def test_reconfigure_with_constant_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with constant values should update entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: "sensor.dc_power",
            CONF_MAX_POWER_AC_TO_DC: "sensor.ac_power",
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # Change to constant values
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: 10.0,
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config contains the constant values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == 10.0
    assert update_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == 8.0


async def test_reconfigure_with_scalar_shows_constant_defaults(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with scalar values should show constant choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values (from prior constant config)
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: 10.0,  # Scalar value
            CONF_MAX_POWER_AC_TO_DC: 8.0,  # Scalar value
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form (user_input=None)
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Check defaults - should have constant choice with scalar values
    defaults = flow._build_defaults("Test Inverter", dict(existing_subentry.data))

    # Defaults should contain constant choice with values
    assert defaults[CONF_SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == 10.0
    assert defaults[CONF_SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == 8.0


async def test_reconfigure_with_string_entity_id_v010_format(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with v0.1.0 string entity ID should show entity choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with v0.1.0 format: string entity IDs (not list, not scalar)
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: "sensor.dc_to_ac_power",  # v0.1.0: single string entity ID
            CONF_MAX_POWER_AC_TO_DC: "sensor.ac_to_dc_power",  # v0.1.0: single string entity ID
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form (user_input=None)
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Check defaults - should have entity choice with the string entity IDs wrapped in lists
    defaults = flow._build_defaults("Test Inverter", dict(existing_subentry.data))

    # Defaults should contain entity choice with the original entity IDs as lists
    assert defaults[CONF_SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == ["sensor.dc_to_ac_power"]
    assert defaults[CONF_SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == ["sensor.ac_to_dc_power"]


async def test_reconfigure_with_entity_list(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with entity list should show entity choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with entity list format
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.dc1", "sensor.dc2"],  # List of entities
            CONF_MAX_POWER_AC_TO_DC: ["sensor.ac"],  # Single entity in list
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults
    defaults = flow._build_defaults("Test Inverter", dict(existing_subentry.data))

    # Defaults should contain entity choice with the entity lists
    assert defaults[CONF_SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == ["sensor.dc1", "sensor.dc2"]
    assert defaults[CONF_SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == ["sensor.ac"]


async def test_reconfigure_selecting_entity_stores_entity_id(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting entity in reconfigure stores the entity ID."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: 10.0,
            CONF_MAX_POWER_AC_TO_DC: 8.0,
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    # Register HAEO number entities in entity registry
    registry = er.async_get(hass)
    dc_to_ac_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_MAX_POWER_DC_TO_AC}",
        suggested_object_id="test_inverter_max_power_dc_to_ac",
    )
    ac_to_dc_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_MAX_POWER_AC_TO_DC}",
        suggested_object_id="test_inverter_max_power_ac_to_dc",
    )

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # User selects entities using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "TestNode",
            CONF_MAX_POWER_DC_TO_AC: [dc_to_ac_entity.entity_id],
            CONF_MAX_POWER_AC_TO_DC: [ac_to_dc_entity.entity_id],
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    # Should complete
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # When entity mode is selected, the entity ID is stored
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_DC_TO_AC] == dc_to_ac_entity.entity_id
    assert update_kwargs["data"][CONF_SECTION_LIMITS][CONF_MAX_POWER_AC_TO_DC] == ac_to_dc_entity.entity_id


# --- Tests for _is_valid_choose_value ---
