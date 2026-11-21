"""Tests for the connection selector and the connections the element flows offer."""

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME, HUB_SECTION_ADVANCED
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows.conftest import create_flow
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.connection_selector import (
    CONNECTION_STRINGS,
    CONNECTION_TRANSLATION_KEY,
    ConnectionSelector,
    ConnectionSelectorConfig,
)

CONFIG: ConnectionSelectorConfig = {
    "element_type": "solar",
    "targets": [
        {"name": "Switchboard", "element_type": "junction", "bus": "ac", "elements": []},
        {"name": "Inverter", "element_type": "inverter", "bus": "dc", "elements": []},
        {"name": "Spare", "element_type": "node", "bus": None, "elements": []},
    ],
}


def test_selector_accepts_only_a_target_it_offers() -> None:
    """The chosen name must be one of the targets."""
    selector = ConnectionSelector(CONFIG)

    assert selector("Inverter") == "Inverter"
    with pytest.raises(vol.Invalid):
        selector("Battery")


def test_selector_config_needs_each_target_s_bus_and_elements() -> None:
    """A target without its bus kind, which may be unknown, is rejected."""
    with pytest.raises(vol.Invalid):
        ConnectionSelector({"element_type": "solar", "targets": [{"name": "Switchboard", "element_type": "junction"}]})


def test_selector_lists_its_strings() -> None:
    """The element's labels are listed with the placeholders it fills in."""
    assert dict(ConnectionSelector.translation_strings()) == {
        ("selector", CONNECTION_TRANSLATION_KEY, "options", key): placeholders
        for key, placeholders in CONNECTION_STRINGS.items()
    }


def _add_connected(hass: HomeAssistant, hub_entry: MockConfigEntry, name: str, element_type: str, target: str) -> None:
    data = {CONF_ELEMENT_TYPE: element_type, CONF_NAME: name, CONF_CONNECTION: as_connection_target(target)}
    hass.config_entries.async_add_subentry(
        hub_entry,
        ConfigSubentry(data=MappingProxyType(data), subentry_type=element_type, title=name, unique_id=None),
    )


def _flow(hass: HomeAssistant, hub_entry: MockConfigEntry, element_type: ElementType) -> ConnectedElementSubentryFlow:
    flow = create_flow(hass, hub_entry, element_type)
    assert isinstance(flow, ConnectedElementSubentryFlow)
    return flow


def _set_advanced_mode(hass: HomeAssistant, hub_entry: MockConfigEntry, *, advanced: bool) -> None:
    data = dict(hub_entry.data)
    data[HUB_SECTION_ADVANCED] = {**data.get(HUB_SECTION_ADVANCED, {}), CONF_ADVANCED_MODE: advanced}
    hass.config_entries.async_update_entry(hub_entry, data=data)


@pytest.fixture
def network(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Add a switchboard, an inverter on it, and a grid and battery on each."""
    add_participant(hass, hub_entry, "Switchboard", ElementType.JUNCTION)
    _add_connected(hass, hub_entry, "Inverter", ElementType.INVERTER, "Switchboard")
    _add_connected(hass, hub_entry, "Grid", ElementType.GRID, "Switchboard")
    _add_connected(hass, hub_entry, "Battery", ElementType.BATTERY, "Inverter")


@pytest.mark.usefixtures("network")
def test_targets_list_what_is_connected_to_each(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Each target lists the elements connected to it."""
    targets = {target["name"]: target for target in _flow(hass, hub_entry, ElementType.SOLAR)._connection_targets(None)}

    assert targets["Switchboard"]["elements"] == [
        {"name": "Inverter", "element_type": "inverter"},
        {"name": "Grid", "element_type": "grid"},
    ]
    assert targets["Inverter"]["elements"] == [{"name": "Battery", "element_type": "battery"}]


@pytest.mark.usefixtures("network")
@pytest.mark.parametrize(
    ("advanced", "switchboard_bus"),
    [
        pytest.param(False, "ac", id="switchboard_is_the_ac_bus"),
        pytest.param(True, None, id="advanced_junction_unknown"),
    ],
)
def test_targets_mark_a_bus_kind_only_when_known(
    hass: HomeAssistant, hub_entry: MockConfigEntry, *, advanced: bool, switchboard_bus: str | None
) -> None:
    """An inverter is a DC bus, and a junction is the AC switchboard only outside advanced mode.

    In advanced mode users make their own junctions and nodes, which may be either.
    """
    _set_advanced_mode(hass, hub_entry, advanced=advanced)
    targets = {target["name"]: target for target in _flow(hass, hub_entry, ElementType.SOLAR)._connection_targets(None)}

    assert targets["Inverter"]["bus"] == "dc"
    assert targets["Switchboard"]["bus"] == switchboard_bus


@pytest.mark.usefixtures("network")
@pytest.mark.parametrize("advanced", [False, True])
@pytest.mark.parametrize(
    ("element_type", "expected"),
    [(ElementType.SOLAR, "Inverter"), (ElementType.BATTERY, "Inverter"), (ElementType.LOAD, "Switchboard")],
)
def test_a_new_element_connects_to_a_bus_of_its_kind(
    hass: HomeAssistant, hub_entry: MockConfigEntry, element_type: ElementType, expected: str, *, advanced: bool
) -> None:
    """DC equipment suggests the inverter's DC bus, and AC equipment an AC bus or one of unknown kind."""
    _set_advanced_mode(hass, hub_entry, advanced=advanced)

    assert _flow(hass, hub_entry, element_type)._current_connection(None) == expected


def test_ac_equipment_prefers_a_bus_of_unknown_kind_over_a_dc_one(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """In advanced mode a load suggests the user's own node before an inverter's DC bus, whatever their order."""
    _set_advanced_mode(hass, hub_entry, advanced=True)
    add_participant(hass, hub_entry, "Inverter", ElementType.INVERTER)
    add_participant(hass, hub_entry, "House bus", ElementType.NODE)

    assert _flow(hass, hub_entry, ElementType.LOAD)._current_connection(None) == "House bus"


def test_dc_equipment_falls_back_to_an_ac_bus_without_an_inverter(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Without a DC bus or one of unknown kind, DC equipment suggests the AC switchboard."""
    _set_advanced_mode(hass, hub_entry, advanced=False)
    add_participant(hass, hub_entry, "Switchboard", ElementType.JUNCTION)

    assert _flow(hass, hub_entry, ElementType.SOLAR)._current_connection(None) == "Switchboard"


@pytest.mark.usefixtures("network")
def test_a_stored_connection_to_a_deleted_element_is_still_offered(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """The form shows a stored connection whose element is gone, so validation can report it."""
    stored = {CONF_CONNECTION: as_connection_target("Old inverter")}
    targets = _flow(hass, hub_entry, ElementType.SOLAR)._connection_targets(stored)

    assert targets[-1] == {"name": "Old inverter", "element_type": "", "bus": None, "elements": []}
