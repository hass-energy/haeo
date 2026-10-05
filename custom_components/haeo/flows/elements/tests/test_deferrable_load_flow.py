"""Tests for deferrable load element config flow."""

from typing import Any
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_calendar_value, as_constant_value
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.deferrable_load import (
    CONF_DEFICIT_PRICE,
    CONF_MAX_POWER,
    CONF_OVERAGE_PRICE,
    CONF_WINDOW_CALENDAR,
    ELEMENT_TYPE,
    SECTION_POWER,
    SECTION_PRICING,
    SECTION_SCHEDULE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.flows.conftest import create_flow


def _user_input(**overrides: Any) -> dict[str, Any]:
    """Build sectioned deferrable load user input."""
    data = {
        CONF_NAME: "Pool Pump",
        CONF_CONNECTION: "TestNode",
        SECTION_SCHEDULE: {CONF_WINDOW_CALENDAR: "calendar.pool_pump"},
        SECTION_PRICING: {CONF_DEFICIT_PRICE: 10.0},
        SECTION_POWER: {CONF_MAX_POWER: 1.5},
    }
    data.update(overrides)
    return data


async def test_user_step_creates_entry_with_calendar(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting stores the calendar schema value and constants."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Pool Pump", "data": {}})

    result = await flow.async_step_user(user_input=_user_input())

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_SCHEDULE][CONF_WINDOW_CALENDAR] == as_calendar_value("calendar.pool_pump")
    assert data[SECTION_PRICING][CONF_DEFICIT_PRICE] == as_constant_value(10.0)
    assert data[SECTION_POWER][CONF_MAX_POWER] == as_constant_value(1.5)


async def test_missing_calendar_is_an_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """The run window calendar is required."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=_user_input(schedule={CONF_WINDOW_CALENDAR: None}))

    assert result.get("type") == FlowResultType.FORM
    assert CONF_WINDOW_CALENDAR in result.get("errors", {})


@pytest.mark.parametrize("field", [CONF_DEFICIT_PRICE, CONF_OVERAGE_PRICE])
def test_penalty_prices_cannot_be_negative(field: str) -> None:
    """Penalty price inputs are bounded below by zero so the optimization stays bounded."""
    field_info = get_input_fields(ELEMENT_TYPE)[SECTION_PRICING][field]

    assert field_info.entity_description.native_min_value == 0.0
