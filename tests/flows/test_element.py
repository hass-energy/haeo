"""Test helper behaviors for element subentry flows."""

from types import MappingProxyType
from typing import cast
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import battery, connection, grid
from custom_components.haeo.elements.battery import BatteryConfigSchema
from custom_components.haeo.flows.element import ElementSubentryFlow, create_subentry_flow_class
from custom_components.haeo.flows.hub import HubConfigFlow


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a hub entry for testing subentry flows."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
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
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
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
    battery_flow_class = subentry_types[battery.ELEMENT_TYPE]
    assert hasattr(battery_flow_class, "__name__")
    assert battery_flow_class.__name__ == "BatterySubentryFlow"

    # Check grid flow
    grid_flow_class = subentry_types[grid.ELEMENT_TYPE]
    assert hasattr(grid_flow_class, "__name__")
    assert grid_flow_class.__name__ == "GridSubentryFlow"

    # Check connection flow
    connection_flow_class = subentry_types[connection.ELEMENT_TYPE]
    assert hasattr(connection_flow_class, "__name__")
    assert connection_flow_class.__name__ == "ConnectionSubentryFlow"


async def test_get_subentries(hass: HomeAssistant) -> None:
    """Test _async_get_subentries retrieves all subentries."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Create subentries using ConfigSubentry
    battery1 = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
                CONF_NAME: "Battery 1",
                battery.CONF_CAPACITY: 10000.0,
                battery.CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_1_soc",
            }
        ),
        subentry_type=battery.ELEMENT_TYPE,
        title="Battery 1",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery1)

    battery2 = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
                CONF_NAME: "Battery 2",
                battery.CONF_CAPACITY: 20000.0,
                battery.CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_2_soc",
            }
        ),
        subentry_type=battery.ELEMENT_TYPE,
        title="Battery 2",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery2)

    # Create flow instance and test _get_other_element_entries
    flow = ElementSubentryFlow(battery.ELEMENT_TYPE, BatteryConfigSchema, {})
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, battery.ELEMENT_TYPE)

    participants = flow._get_other_element_entries()

    # Should have both batteries
    assert len(participants) == 2
    assert "Battery 1" in participants
    assert "Battery 2" in participants
    battery1_config = cast("BatteryConfigSchema", participants["Battery 1"])
    battery2_config = cast("BatteryConfigSchema", participants["Battery 2"])
    assert battery1_config[battery.CONF_CAPACITY] == 10000.0
    assert battery2_config[battery.CONF_CAPACITY] == 20000.0


async def test_get_subentries_with_exclusion(hass: HomeAssistant) -> None:
    """Test _async_get_subentries with exclusion for reconfigure."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Create subentries using ConfigSubentry
    battery1 = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
                CONF_NAME: "Battery 1",
                battery.CONF_CAPACITY: 10000.0,
                battery.CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_1_soc",
            }
        ),
        subentry_type=battery.ELEMENT_TYPE,
        title="Battery 1",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery1)

    battery2 = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
                CONF_NAME: "Battery 2",
                battery.CONF_CAPACITY: 20000.0,
                battery.CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_2_soc",
            }
        ),
        subentry_type=battery.ELEMENT_TYPE,
        title="Battery 2",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, battery2)

    # Create flow instance and test with exclusion
    flow = ElementSubentryFlow(battery.ELEMENT_TYPE, BatteryConfigSchema, {})
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, battery.ELEMENT_TYPE)  # type: ignore[assignment]

    # Get subentry ID for battery1 to exclude it
    battery1_id = None
    for subentry_id, subentry in hub_entry.subentries.items():
        if subentry.data.get(CONF_NAME) == "Battery 1":
            battery1_id = subentry_id
            break

    assert battery1_id is not None

    flow._get_reconfigure_subentry = MagicMock(return_value=hub_entry.subentries[battery1_id])

    participants = flow._get_other_element_entries()

    # Should only have battery2
    assert len(participants) == 1
    assert "Battery 1" not in participants
    assert "Battery 2" in participants


async def test_create_subentry_flow_class() -> None:
    """Test create_subentry_flow_class creates properly configured flow class."""
    defaults = {
        battery.CONF_CAPACITY: 10000.0,
        battery.CONF_MAX_CHARGE_POWER: 5000.0,
    }
    flow_class = create_subentry_flow_class(battery.ELEMENT_TYPE, BatteryConfigSchema, defaults)

    # Check class attributes - name is formatted from element type
    assert flow_class.__name__ == "BatterySubentryFlow"

    # Create instance and check it has correct attributes
    flow_instance = flow_class()  # type: ignore[call-arg]
    assert flow_instance.element_type == battery.ELEMENT_TYPE
    assert flow_instance.schema_cls == BatteryConfigSchema
    assert flow_instance.defaults == defaults
