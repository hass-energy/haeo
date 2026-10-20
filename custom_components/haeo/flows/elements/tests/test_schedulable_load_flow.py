"""Tests for schedulable load element config flow."""

from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.schedulable_load import (
    CONF_DEFICIT_PRICE,
    CONF_DURATION,
    CONF_INTEGER_MODE,
    CONF_POWER,
    CONF_WINDOW_CALENDAR,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_PRICING,
    SECTION_PROFILE,
    SECTION_SCHEDULE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.flows.conftest import create_flow


def _user_input(**overrides: object) -> dict[str, object]:
    """Build sectioned schedulable load user input."""
    data: dict[str, object] = {
        CONF_NAME: "Dishwasher",
        CONF_CONNECTION: "TestNode",
        SECTION_SCHEDULE: {CONF_WINDOW_CALENDAR: "calendar.dishwasher"},
        SECTION_PROFILE: {CONF_POWER: 1.8, CONF_DURATION: 2.5},
        SECTION_PRICING: {CONF_DEFICIT_PRICE: 10.0},
        SECTION_ADVANCED: {CONF_INTEGER_MODE: "all"},
    }
    data.update(overrides)
    return data


async def test_user_step_stores_profile_and_integer_mode(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting stores the calendar, the profile constants, and the integer mode."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Dishwasher", "data": {}}
    )

    result = await flow.async_step_user(user_input=_user_input())

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_SCHEDULE][CONF_WINDOW_CALENDAR] == as_entity_value(["calendar.dishwasher"])
    assert data[SECTION_PROFILE][CONF_POWER] == as_constant_value(1.8)
    assert data[SECTION_PROFILE][CONF_DURATION] == as_constant_value(2.5)
    assert data[SECTION_ADVANCED][CONF_INTEGER_MODE] == "all"


@pytest.mark.parametrize(
    ("subentry_data", "expected"),
    [
        pytest.param(None, "first", id="new_load_defaults_to_start_now"),
        pytest.param({SECTION_ADVANCED: {CONF_INTEGER_MODE: "none"}}, "none", id="reconfigure_keeps_stored_mode"),
    ],
)
def test_integer_mode_default(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    subentry_data: dict[str, object] | None,
    expected: str,
) -> None:
    """The integer mode defaults to integer start-now decisions and keeps a stored choice."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    defaults = flow._build_defaults("Dishwasher", get_input_fields(ELEMENT_TYPE), subentry_data)

    assert defaults[SECTION_ADVANCED][CONF_INTEGER_MODE] == expected
