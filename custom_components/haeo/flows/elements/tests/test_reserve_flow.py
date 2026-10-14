"""Tests for the reserve element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import SelectSelector
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from conftest import add_participant
from custom_components.haeo import _cleanup_reserve_participants
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.reserve import (
    CONF_GENERATION,
    CONF_LOADS,
    CONF_MINIMUM,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    ELEMENT_TYPE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)
from custom_components.haeo.flows.conftest import create_flow


def _add_elements(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    for name, element_type in (
        ("House", ElementType.LOAD),
        ("Solar", ElementType.SOLAR),
        ("Battery", ElementType.BATTERY),
        ("Grid", ElementType.GRID),
        ("Bus", ElementType.NODE),
    ):
        add_participant(hass, hub_entry, name, element_type)


def _user_input(**participants: list[str]) -> dict[str, object]:
    return {
        CONF_NAME: "Backup",
        SECTION_PARTICIPANTS: participants,
        SECTION_REQUIREMENT: {CONF_WINDOW: 12.0, CONF_MINIMUM: 2.0},
        SECTION_PRICING: {CONF_SHORTFALL_COST: 0.05},
    }


def _section_options(schema: vol.Schema, section_key: str) -> dict[str, list[str]]:
    """Return the options each select selector in a form section offers."""
    section = next(value for key, value in schema.schema.items() if key == section_key)
    return {
        str(key): list(selector.config["options"])
        for key, selector in section.schema.schema.items()
        if isinstance(selector, SelectSelector)
    }


REQUIREMENT_TYPES = pytest.mark.parametrize("element_type", [ElementType.RESERVE, ElementType.HEADROOM])


@REQUIREMENT_TYPES
async def test_participant_lists_offer_loads_generation_and_batteries(
    hass: HomeAssistant, hub_entry: MockConfigEntry, element_type: ElementType
) -> None:
    """Each participant list offers only the elements that fit it."""
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, element_type)

    result = await flow.async_step_user(user_input=None)

    assert _section_options(result["data_schema"], SECTION_PARTICIPANTS) == {
        CONF_LOADS: ["House"],
        CONF_GENERATION: ["Solar"],
        CONF_STORAGE: ["Battery"],
    }


@REQUIREMENT_TYPES
async def test_requirement_needs_a_battery(
    hass: HomeAssistant, hub_entry: MockConfigEntry, element_type: ElementType
) -> None:
    """A reserve or headroom without a battery to hold it is rejected."""
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, element_type)

    result = await flow.async_step_user(user_input=_user_input(loads=["House"]))

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"base": "reserve_storage_required"}


async def test_reconfigure_keeps_participants_and_stores_inputs(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Reconfiguring prefills the participants and stores the inputs as schema values."""
    _add_elements(hass, hub_entry)
    stored = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Backup",
        SECTION_PARTICIPANTS: {CONF_LOADS: ["House"], CONF_STORAGE: ["Battery"]},
        SECTION_REQUIREMENT: {CONF_WINDOW: as_constant_value(6.0), CONF_MINIMUM: as_constant_value(1.0)},
        SECTION_PRICING: {CONF_SHORTFALL_COST: as_constant_value(0.1)},
    }
    subentry = ConfigSubentry(data=MappingProxyType(stored), subentry_type=ELEMENT_TYPE, title="Backup", unique_id=None)
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT})

    form = await flow.async_step_reconfigure(user_input=None)
    participants = _section_options(form["data_schema"], SECTION_PARTICIPANTS)
    await flow.async_step_reconfigure(
        user_input=_user_input(loads=["House"], generation=["Solar"], storage=["Battery"])
    )

    assert participants[CONF_LOADS] == ["House"]
    data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert data[SECTION_PARTICIPANTS] == {CONF_LOADS: ["House"], CONF_GENERATION: ["Solar"], CONF_STORAGE: ["Battery"]}
    assert data[SECTION_REQUIREMENT] == {CONF_WINDOW: as_constant_value(12.0), CONF_MINIMUM: as_constant_value(2.0)}


@REQUIREMENT_TYPES
@pytest.mark.parametrize(
    ("loads", "expected_loads"),
    [
        pytest.param(["House", "Pool"], ["House"], id="deleted_load_removed"),
        pytest.param(["House"], ["House"], id="unchanged"),
    ],
)
def test_cleanup_strips_deleted_elements_from_reserves(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    loads: list[str],
    expected_loads: list[str],
    element_type: ElementType,
) -> None:
    """Deleting an element removes it from every reserve that named it."""
    add_participant(hass, hub_entry, "House", ElementType.LOAD)
    add_participant(hass, hub_entry, "Battery", ElementType.BATTERY)
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: element_type,
                CONF_NAME: "Backup",
                SECTION_PARTICIPANTS: {CONF_LOADS: loads, CONF_STORAGE: ["Battery"]},
            }
        ),
        subentry_type=element_type,
        title="Backup",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    _cleanup_reserve_participants(hass, hub_entry)

    participants = hub_entry.subentries[subentry.subentry_id].data[SECTION_PARTICIPANTS]
    assert participants == {CONF_LOADS: expected_loads, CONF_STORAGE: ["Battery"]}
