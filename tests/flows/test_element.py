"""Test helper behaviors for element subentry flows."""

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import battery, connection, grid
from custom_components.haeo.flows.hub import HubConfigFlow


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a hub entry for testing subentry flows."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            "basic": {CONF_NAME: "Test Hub"},
            "advanced": {},
        },
        entry_id="hub_id",
    )
    entry.add_to_hass(hass)
    return entry


async def test_subentry_flow_classes_have_correct_attributes(hass: HomeAssistant) -> None:
    """Test that subentry flow classes have the expected attributes."""
    # Create hub entry with advanced mode enabled to access connection flows
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            "basic": {CONF_NAME: "Test Hub"},
            "advanced": {CONF_ADVANCED_MODE: True},  # Required for connection flows
        },
        entry_id="hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Get supported subentry types
    flow_handler = HubConfigFlow()
    flow_handler.hass = hass
    subentry_types = flow_handler.async_get_supported_subentry_types(hub_entry)

    # Check battery flow
    battery_flow_class = subentry_types[battery.ELEMENT_TYPE]
    assert hasattr(battery_flow_class, "__name__")
    assert battery_flow_class.__name__ == "BatterySubentryFlowHandler"

    # Check grid flow
    grid_flow_class = subentry_types[grid.ELEMENT_TYPE]
    assert hasattr(grid_flow_class, "__name__")
    assert grid_flow_class.__name__ == "GridSubentryFlowHandler"

    # Check connection flow
    connection_flow_class = subentry_types[connection.ELEMENT_TYPE]
    assert hasattr(connection_flow_class, "__name__")
    assert connection_flow_class.__name__ == "ConnectionSubentryFlowHandler"
