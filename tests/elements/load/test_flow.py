"""Tests for load element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import node
from custom_components.haeo.elements.load import (
    CONF_CONNECTION,
    CONF_FORECAST,
    ELEMENT_TYPE,
    SECTION_DETAILS,
    SECTION_FORECAST,
)

from ..conftest import add_participant, create_flow


def _wrap_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat load input values into sectioned config."""
    if SECTION_DETAILS in flat:
        return dict(flat)
    return {
        SECTION_DETAILS: {
            CONF_NAME: flat[CONF_NAME],
            CONF_CONNECTION: flat[CONF_CONNECTION],
        },
        SECTION_FORECAST: {
            CONF_FORECAST: flat[CONF_FORECAST],
        },
    }


def _wrap_config(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat load config values into sectioned config with element type."""
    if SECTION_DETAILS in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **_wrap_input(flat)}


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Load reconfigure should include deleted connection target in options."""
    # Create load that references a deleted connection target
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "DeletedNode",  # This node no longer exists
            CONF_FORECAST: ["sensor.power"],
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Load",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - should not error
    # Entity-first pattern uses step_id="user" for both new and reconfigure
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


async def test_get_subentry_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_subentry should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # During user flow, _get_reconfigure_subentry will raise
    subentry = flow._get_subentry()

    assert subentry is None


async def test_reconfigure_with_string_entity_id_v010_format(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with v0.1.0 string entity ID should show entity in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with v0.1.0 format: string entity ID (not list, not scalar)
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: "sensor.load_forecast",  # Simulating v0.1.0 single string entity ID
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Load",
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

    # Check defaults - should have entity choice with the string entity ID wrapped in a list
    defaults = flow._build_defaults("Test Load", dict(existing_subentry.data))

    # Defaults should contain entity choice with original entity ID as list
    assert defaults[SECTION_FORECAST][CONF_FORECAST] == ["sensor.load_forecast"]


async def test_reconfigure_with_scalar_shows_constant_defaults(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with scalar value should show constant choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar value (from constant config)
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: 100.0,  # Scalar value, not entity link
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Load",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults - should resolve to constant choice with the scalar value
    defaults = flow._build_defaults("Test Load", dict(existing_subentry.data))

    # Defaults should contain constant choice with the scalar value
    assert defaults[SECTION_FORECAST][CONF_FORECAST] == 100.0


async def test_reconfigure_with_missing_field_shows_none_default(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with missing field should show None in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry without forecast field (simulating missing optional field)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        SECTION_DETAILS: {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
        },
        SECTION_FORECAST: {},
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Load",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults - missing field should show None
    defaults = flow._build_defaults("Test Load", dict(existing_subentry.data))

    # Missing field should result in None default
    assert defaults.get(SECTION_FORECAST, {}).get(CONF_FORECAST) is None


async def test_user_step_with_entity_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with entity selection should create entry with entity ID."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Load",
            "data": {},
        }
    )

    # Submit with entity selection using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: ["sensor.load_forecast"],
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity ID as string
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_FORECAST][CONF_FORECAST] == "sensor.load_forecast"


async def test_user_step_with_constant_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with constant value should create entry with value."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Load",
            "data": {},
        }
    )

    # Submit with constant value using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: 5.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant value
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_FORECAST][CONF_FORECAST] == 5.0


async def test_user_step_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with empty required field should show validation error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit with empty forecast (required field)
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "TestNode",
            CONF_FORECAST: [],  # Empty list = invalid
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert CONF_FORECAST in result.get("errors", {})


# --- Tests for _is_valid_choose_value ---
