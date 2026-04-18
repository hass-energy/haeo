"""Test that participant name resolution works after config entry deserialization.

After HA restart, subentry data values are deserialized as plain strings,
not as enum instances. The participant name resolution must handle both.
"""

from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.flows.conftest import create_flow


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a hub config entry."""
    entry = MockConfigEntry(
        domain="haeo",
        title="Test Hub",
        data={"integration_type": "hub", "common": {"name": "Test", "horizon_preset": "2_days"}},
    )
    entry.add_to_hass(hass)
    return entry


def _add_subentry(hass: HomeAssistant, hub_entry: MockConfigEntry, *, element_type: Any, title: str) -> None:
    """Add a subentry with the given element_type value."""
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: element_type, CONF_NAME: title}),
        subentry_type=str(element_type),
        title=title,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)


async def test_participant_names_with_enum_element_type(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Participant names resolve when element_type is an ElementType enum instance."""
    _add_subentry(hass, hub_entry, element_type=ElementType.NODE, title="Switchboard")
    _add_subentry(hass, hub_entry, element_type=ElementType.INVERTER, title="Inverter")

    flow = create_flow(hass, hub_entry, ElementType.INVERTER)
    participants = flow._get_participant_names()
    assert "Switchboard" in participants


async def test_participant_names_with_string_element_type(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Participant names resolve when element_type is a plain string after deserialization."""
    _add_subentry(hass, hub_entry, element_type="node", title="Switchboard")
    _add_subentry(hass, hub_entry, element_type="inverter", title="Inverter")

    flow = create_flow(hass, hub_entry, ElementType.INVERTER)
    participants = flow._get_participant_names()
    assert "Switchboard" in participants
