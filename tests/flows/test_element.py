"""Test helper behaviors for element subentry flows."""

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_NAME, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.elements.battery import BatteryConfigSchema
from custom_components.haeo.flows.element import ElementSubentryFlow, create_subentry_flow_class
from custom_components.haeo.flows.hub import HubConfigFlow


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a hub entry for testing subentry flows."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_id",
    )
    entry.add_to_hass(hass)
    return entry


async def test_subentry_flow_classes_have_correct_attributes(hass: HomeAssistant) -> None:
    """Test that subentry flow classes have the expected attributes."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Get supported subentry types
    flow_handler = HubConfigFlow()
    flow_handler.hass = hass
    subentry_types = flow_handler.async_get_supported_subentry_types(hub_entry)

    # Check battery flow
    battery_flow_class = subentry_types["battery"]
    assert hasattr(battery_flow_class, "__name__")
    assert battery_flow_class.__name__ == "BatterySubentryFlow"

    # Check grid flow
    grid_flow_class = subentry_types["grid"]
    assert hasattr(grid_flow_class, "__name__")
    assert grid_flow_class.__name__ == "GridSubentryFlow"

    # Check connection flow
    connection_flow_class = subentry_types["connection"]
    assert hasattr(connection_flow_class, "__name__")
    assert connection_flow_class.__name__ == "ConnectionSubentryFlow"


async def test_get_subentries(hass: HomeAssistant) -> None:
    """Test _async_get_subentries retrieves all subentries."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Create subentries using ConfigSubentry
    battery1 = ConfigSubentry(
        data=MappingProxyType(
            {
                "name_value": "Battery 1",
                "capacity_value": 10000.0,
            }
        ),
        subentry_type="battery",
        title="Battery 1",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery1)

    battery2 = ConfigSubentry(
        data=MappingProxyType(
            {
                "name_value": "Battery 2",
                "capacity_value": 20000.0,
            }
        ),
        subentry_type="battery",
        title="Battery 2",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery2)

    # Create flow instance and test _get_participant_entries
    flow = ElementSubentryFlow("battery", BatteryConfigSchema, {})
    flow.hass = hass

    participants = flow._get_participant_entries(hub_entry.entry_id)

    # Should have both batteries
    assert len(participants) == 2
    assert "Battery 1" in participants
    assert "Battery 2" in participants
    assert participants["Battery 1"]["capacity_value"] == 10000.0
    assert participants["Battery 2"]["capacity_value"] == 20000.0


async def test_get_subentries_with_exclusion(hass: HomeAssistant) -> None:
    """Test _async_get_subentries with exclusion for reconfigure."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Create subentries using ConfigSubentry
    battery1 = ConfigSubentry(
        data=MappingProxyType(
            {
                "name_value": "Battery 1",
                "capacity_value": 10000.0,
            }
        ),
        subentry_type="battery",
        title="Battery 1",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery1)

    battery2 = ConfigSubentry(
        data=MappingProxyType(
            {
                "name_value": "Battery 2",
                "capacity_value": 20000.0,
            }
        ),
        subentry_type="battery",
        title="Battery 2",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery2)

    # Create flow instance and test with exclusion
    flow = ElementSubentryFlow("battery", BatteryConfigSchema, {})
    flow.hass = hass

    # Get subentry ID for battery1 to exclude it
    battery1_id = None
    for subentry_id, subentry in hub_entry.subentries.items():
        if subentry.data.get("name_value") == "Battery 1":
            battery1_id = subentry_id
            break

    participants = flow._get_participant_entries(hub_entry.entry_id, exclude_subentry_id=battery1_id)

    # Should only have battery2
    assert len(participants) == 1
    assert "Battery 1" not in participants
    assert "Battery 2" in participants


async def test_create_subentry_flow_class() -> None:
    """Test create_subentry_flow_class creates properly configured flow class."""
    defaults = {"capacity": 10000.0, "charge_rate": 5000.0}
    flow_class = create_subentry_flow_class("battery", BatteryConfigSchema, defaults)

    # Check class attributes - name is formatted from element type
    assert flow_class.__name__ == "BatterySubentryFlow"

    # Create instance and check it has correct attributes
    flow_instance = flow_class()  # type: ignore[call-arg]
    assert flow_instance.element_type == "battery"
    assert flow_instance.schema_cls == BatteryConfigSchema
    assert flow_instance.defaults == defaults
