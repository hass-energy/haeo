"""Tests for grid element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import node
from custom_components.haeo.elements.grid import CONF_CONNECTION, CONF_EXPORT_PRICE, CONF_IMPORT_PRICE, ELEMENT_TYPE
from custom_components.haeo.flows.field_schema import MODE_SUFFIX, InputMode

from ..conftest import add_participant, create_flow


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Grid reconfigure should include deleted connection target in options."""
    # Create grid that references a deleted connection target
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "DeletedNode",  # This node no longer exists
        CONF_IMPORT_PRICE: ["sensor.import"],
        CONF_EXPORT_PRICE: ["sensor.export"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
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


async def test_schema_uses_default_when_mode_is_none_for_import_price(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When import price mode is NONE, the field should not appear in step 2 schema."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Complete step 1 with NONE mode for import price (will use default)
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        f"{CONF_IMPORT_PRICE}{MODE_SUFFIX}": InputMode.NONE,
        f"{CONF_EXPORT_PRICE}{MODE_SUFFIX}": InputMode.CONSTANT,
    }
    result = await flow.async_step_user(user_input=step1_input)

    # Should proceed to values step
    assert result.get("step_id") == "values"
    schema = result.get("data_schema")

    # NONE mode means import_price is not in the schema
    # Only export_price should be present
    validated = schema(
        {
            CONF_EXPORT_PRICE: 0.05,
        }
    )
    assert CONF_IMPORT_PRICE not in validated


async def test_schema_uses_default_when_mode_is_none_for_export_price(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When export price mode is NONE, the field should not appear in step 2 schema."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Complete step 1 with NONE mode for export price (will use default)
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        f"{CONF_IMPORT_PRICE}{MODE_SUFFIX}": InputMode.CONSTANT,
        f"{CONF_EXPORT_PRICE}{MODE_SUFFIX}": InputMode.NONE,
    }
    result = await flow.async_step_user(user_input=step1_input)

    # Should proceed to values step
    assert result.get("step_id") == "values"
    schema = result.get("data_schema")

    # NONE mode means export_price is not in the schema
    # Only import_price should be present
    validated = schema(
        {
            CONF_IMPORT_PRICE: 0.30,
        }
    )
    assert CONF_EXPORT_PRICE not in validated
