"""Tests for grid element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import node
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
    ELEMENT_TYPE,
)

from ..conftest import add_participant, create_flow


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Grid reconfigure should include deleted connection target in options."""
    # Create grid that references a deleted connection target
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "DeletedNode",  # This node no longer exists
        CONF_IMPORT_PRICE: 0.30,
        CONF_EXPORT_PRICE: 0.05,
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
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

    # Submit with empty import_price (required field) - entity choice with empty list
    user_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [],
        CONF_EXPORT_PRICE: 0.05,
    }
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


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
            "title": "Test Grid",
            "data": {},
        }
    )

    # Submit with constant values using choose selector format
    user_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: 0.25,
        CONF_EXPORT_PRICE: 0.05,
        CONF_IMPORT_LIMIT: 10.0,
        CONF_EXPORT_LIMIT: 10.0,
    }
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][CONF_IMPORT_PRICE] == 0.25
    assert create_kwargs["data"][CONF_EXPORT_PRICE] == 0.05


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
            "title": "Test Grid",
            "data": {},
        }
    )

    # Submit with entity selections
    user_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: ["sensor.import_price"],
        CONF_EXPORT_PRICE: ["sensor.export_price"],
        CONF_IMPORT_LIMIT: 10.0,
        CONF_EXPORT_LIMIT: 10.0,
    }
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity IDs as strings (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][CONF_IMPORT_PRICE] == "sensor.import_price"
    assert create_kwargs["data"][CONF_EXPORT_PRICE] == "sensor.export_price"


# --- Tests for reconfigure flow ---


async def test_reconfigure_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with empty required field should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: 0.30,
        CONF_EXPORT_PRICE: 0.05,
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Submit with empty import_price (required field)
    user_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [],
        CONF_EXPORT_PRICE: 0.05,
    }
    result = await flow.async_step_reconfigure(user_input=user_input)

    # Should show reconfigure form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


async def test_reconfigure_with_constant_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with constant values should update entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with entity links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: "sensor.import",
        CONF_EXPORT_PRICE: "sensor.export",
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # Change to constant values
    user_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: 0.30,
        CONF_EXPORT_PRICE: 0.08,
    }
    result = await flow.async_step_reconfigure(user_input=user_input)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config contains the constant values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][CONF_IMPORT_PRICE] == 0.30
    assert update_kwargs["data"][CONF_EXPORT_PRICE] == 0.08


async def test_reconfigure_with_scalar_shows_constant_defaults(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with scalar values should show constant choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values (from prior constant config)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: 0.30,  # Scalar value
        CONF_EXPORT_PRICE: 0.08,  # Scalar value
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
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
    defaults = flow._build_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain constant choice with values
    assert defaults[CONF_IMPORT_PRICE] == 0.30
    assert defaults[CONF_EXPORT_PRICE] == 0.08


async def test_reconfigure_with_string_entity_id_v010_format(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with v0.1.0 string entity ID should show entity choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with v0.1.0 format: string entity IDs (not list, not scalar)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: "sensor.import_price",  # v0.1.0: single string entity ID
        CONF_EXPORT_PRICE: "sensor.export_price",  # v0.1.0: single string entity ID
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
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
    defaults = flow._build_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain entity choice with the original entity IDs as lists
    assert defaults[CONF_IMPORT_PRICE] == ["sensor.import_price"]
    assert defaults[CONF_EXPORT_PRICE] == ["sensor.export_price"]


async def test_reconfigure_with_entity_list(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with entity list should show entity choice in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with entity list format
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: ["sensor.import1", "sensor.import2"],  # List of entities
        CONF_EXPORT_PRICE: ["sensor.export"],  # Single entity in list
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Check defaults
    defaults = flow._build_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain entity choice with the entity lists
    assert defaults[CONF_IMPORT_PRICE] == ["sensor.import1", "sensor.import2"]
    assert defaults[CONF_EXPORT_PRICE] == ["sensor.export"]
