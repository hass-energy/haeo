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

from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.flows import HUB_SECTION_ADVANCED
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


@pytest.mark.parametrize(
    ("advanced_mode", "expected"),
    [
        pytest.param(False, ["Inverter", "Node"], id="standard"),
        pytest.param(True, ["Battery Section", "Inverter", "Node"], id="advanced"),
    ],
)
async def test_participant_names_exclude_elements_with_own_connections(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    advanced_mode: bool,
    expected: list[str],
) -> None:
    """Grid, battery, solar, and load are never endpoints, even in advanced mode."""
    hass.config_entries.async_update_entry(
        hub_entry,
        data={**hub_entry.data, HUB_SECTION_ADVANCED: {CONF_ADVANCED_MODE: advanced_mode}},
    )
    for element_type in ElementType:
        _add_subentry(hass, hub_entry, element_type=element_type, title=element_type.replace("_", " ").title())

    flow = create_flow(hass, hub_entry, ElementType.CONNECTION)

    assert flow._get_participant_names() == expected
