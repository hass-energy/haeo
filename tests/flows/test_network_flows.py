"""Comprehensive tests for network subentry flows."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.flows.network import NetworkSubentryFlow


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a hub entry for testing network flows."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)
    return entry


async def test_network_flow_user_step_success(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Test successful network creation through user step."""
    flow = NetworkSubentryFlow()
    flow.hass = hass

    # Mock the parent entry and create_entry
    flow._get_entry = Mock(return_value=hub_entry)  # type: ignore[method-assign]
    create_entry_result = {"type": FlowResultType.CREATE_ENTRY, "title": "Network", "data": {}}
    flow.async_create_entry = Mock(return_value=create_entry_result)  # type: ignore[method-assign]

    # First call - show form
    result = await flow.async_step_user(user_input=None)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "errors" in result
    assert not result["errors"]

    # Second call - submit data
    user_input = {
        "name_value": "Network",
    }
    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Network"

    # Verify async_create_entry was called with correct data
    flow.async_create_entry.assert_called_once()
    call_kwargs = flow.async_create_entry.call_args.kwargs
    assert call_kwargs["title"] == "Network"
    assert call_kwargs["data"]["name_value"] == "Network"
    assert call_kwargs["data"][CONF_ELEMENT_TYPE] == "network"


async def test_network_flow_user_step_missing_name(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Test network creation with missing name."""
    flow = NetworkSubentryFlow()
    flow.hass = hass
    flow._get_entry = Mock(return_value=hub_entry)  # type: ignore[method-assign]

    # Submit with empty name
    user_input = {
        "name_value": "",
    }
    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"name_value": "missing_name"}


async def test_network_flow_user_step_network_exists(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Test network creation when network already exists."""
    # Add existing network subentry
    existing_network = ConfigSubentry(
        data=MappingProxyType(
            {
                "name_value": "Existing Network",
            }
        ),
        subentry_type="network",
        title="Existing Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_network)

    flow = NetworkSubentryFlow()
    flow.hass = hass
    flow._get_entry = Mock(return_value=hub_entry)  # type: ignore[method-assign]

    # Try to create another network
    user_input = {
        "name_value": "New Network",
    }
    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"name_value": "network_exists"}


async def test_network_flow_reconfigure_success(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Test successful network reconfiguration."""
    # Add existing network
    existing_network = ConfigSubentry(
        data=MappingProxyType(
            {
                "name_value": "Old Network",
            }
        ),
        subentry_type="network",
        title="Old Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_network)

    flow = NetworkSubentryFlow()
    flow.hass = hass
    flow._get_entry = Mock(return_value=hub_entry)  # type: ignore[method-assign]
    flow._get_reconfigure_subentry = Mock(return_value=existing_network)  # type: ignore[method-assign]

    # Mock async_update_reload_and_abort
    abort_result = {"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
    flow.async_update_reload_and_abort = Mock(return_value=abort_result)  # type: ignore[method-assign]

    # First call - show form with current values
    result = await flow.async_step_reconfigure(user_input=None)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # Second call - update name
    user_input = {
        "name_value": "New Network Name",
    }
    result = await flow.async_step_reconfigure(user_input=user_input)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    # Verify update was called with correct data
    flow.async_update_reload_and_abort.assert_called_once()
    call_args = flow.async_update_reload_and_abort.call_args.args
    call_kwargs = flow.async_update_reload_and_abort.call_args.kwargs
    assert call_args[0] == hub_entry
    assert call_args[1] == existing_network
    assert call_kwargs["title"] == "New Network Name"
    assert call_kwargs["data"]["name_value"] == "New Network Name"
    assert call_kwargs["data"][CONF_ELEMENT_TYPE] == "network"


async def test_network_flow_reconfigure_missing_name(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Test network reconfiguration with missing name."""
    existing_network = ConfigSubentry(
        data=MappingProxyType({"name_value": "Network"}),
        subentry_type="network",
        title="Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_network)

    flow = NetworkSubentryFlow()
    flow.hass = hass
    flow._get_entry = Mock(return_value=hub_entry)  # type: ignore[method-assign]
    flow._get_reconfigure_subentry = Mock(return_value=existing_network)  # type: ignore[method-assign]

    # Submit with empty name
    user_input = {
        "name_value": "",
    }
    result = await flow.async_step_reconfigure(user_input=user_input)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"name_value": "missing_name"}


async def test_network_flow_remove_subentry_prevented(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Test that network removal is prevented."""
    flow = NetworkSubentryFlow()
    flow.hass = hass
    flow._get_entry = Mock(return_value=hub_entry)  # type: ignore[method-assign]

    # Try to remove network
    result = await flow.async_step_remove_subentry(_user_input=None)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "cannot_remove_network"
