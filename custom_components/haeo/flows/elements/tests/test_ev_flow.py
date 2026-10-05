"""Tests for EV element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    as_calendar_value,
    as_constant_value,
    as_entity_value,
    get_schema_value_kinds,
)
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.ev import (
    CONF_CAPACITY,
    CONF_CONNECTED,
    CONF_CURRENT_SOC,
    CONF_ENERGY_PER_DISTANCE,
    CONF_MAX_CHARGE_RATE,
    CONF_ODOMETER,
    CONF_ODOMETER_AT_DISCONNECT,
    CONF_PUBLIC_CHARGING_PRICE,
    CONF_RESERVE_PRICE,
    CONF_TRIP_CALENDAR,
    ELEMENT_TYPE,
    SECTION_CHARGING,
    SECTION_PUBLIC_CHARGING,
    SECTION_TRIP,
    SECTION_VEHICLE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION, SECTION_EFFICIENCY, SECTION_POWER_LIMITS
from custom_components.haeo.elements import get_input_field_schema_info, get_input_fields
from custom_components.haeo.flows.conftest import create_flow


def _user_input(trip: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build sectioned EV user input with sensible defaults."""
    return {
        CONF_NAME: "Test EV",
        CONF_CONNECTION: "TestNode",
        SECTION_VEHICLE: {
            CONF_CAPACITY: 60.0,
            CONF_ENERGY_PER_DISTANCE: 0.15,
            CONF_CURRENT_SOC: ["sensor.ev_soc"],
        },
        SECTION_CHARGING: {
            CONF_MAX_CHARGE_RATE: 7.4,
        },
        SECTION_TRIP: trip or {},
        SECTION_PUBLIC_CHARGING: {},
        SECTION_POWER_LIMITS: {},
        SECTION_EFFICIENCY: {},
    }


async def test_user_step_creates_entry_with_calendar(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with a trip calendar stores a calendar schema value."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test EV", "data": {}})

    user_input = _user_input(
        trip={
            CONF_TRIP_CALENDAR: "calendar.ev_trips",
            CONF_CONNECTED: ["binary_sensor.ev_plugged_in"],
            CONF_ODOMETER: ["sensor.ev_odometer"],
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_TRIP][CONF_TRIP_CALENDAR] == as_calendar_value("calendar.ev_trips")
    assert data[SECTION_TRIP][CONF_CONNECTED] == as_entity_value(["binary_sensor.ev_plugged_in"])
    assert data[SECTION_TRIP][CONF_ODOMETER] == as_entity_value(["sensor.ev_odometer"])
    assert data[SECTION_VEHICLE][CONF_CAPACITY] == as_constant_value(60.0)
    assert data[SECTION_VEHICLE][CONF_CURRENT_SOC] == as_entity_value(["sensor.ev_soc"])


async def test_user_step_without_trip_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """The trip section is optional; a minimal EV still creates an entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test EV", "data": {}})

    result = await flow.async_step_user(user_input=_user_input())

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert CONF_TRIP_CALENDAR not in data[SECTION_TRIP]


async def test_reconfigure_defaults_surface_calendar_entity(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure defaults surface the stored calendar entity ID."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    from custom_components.haeo.core.schema import as_connection_target  # noqa: PLC0415

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test EV",
        CONF_CONNECTION: as_connection_target("TestNode"),
        SECTION_VEHICLE: {
            CONF_CAPACITY: as_constant_value(60.0),
            CONF_ENERGY_PER_DISTANCE: as_constant_value(0.15),
            CONF_CURRENT_SOC: as_entity_value(["sensor.ev_soc"]),
        },
        SECTION_CHARGING: {CONF_MAX_CHARGE_RATE: as_constant_value(7.4)},
        SECTION_TRIP: {
            CONF_TRIP_CALENDAR: as_calendar_value("calendar.ev_trips"),
            CONF_ODOMETER_AT_DISCONNECT: as_entity_value(["sensor.odo_disc"]),
        },
        SECTION_PUBLIC_CHARGING: {},
        SECTION_POWER_LIMITS: {},
        SECTION_EFFICIENCY: {},
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test EV",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    result = await flow.async_step_reconfigure(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields({CONF_ELEMENT_TYPE: ELEMENT_TYPE})
    defaults = flow._build_defaults("Test EV", input_fields, dict(existing_subentry.data))
    assert defaults[SECTION_TRIP][CONF_TRIP_CALENDAR] == "calendar.ev_trips"
    assert defaults[SECTION_TRIP][CONF_ODOMETER_AT_DISCONNECT] == ["sensor.odo_disc"]


async def test_new_entry_leaves_plugged_in_sensor_unset(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """A new EV does not pre-fill a plugged-in state that would override the trip calendar."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    input_fields = get_input_fields({CONF_ELEMENT_TYPE: ELEMENT_TYPE})
    defaults = flow._build_defaults("Test EV", input_fields)

    assert CONF_CONNECTED not in defaults[SECTION_TRIP]


def test_plugged_in_field_accepts_only_a_live_sensor() -> None:
    """A constant plugged-in state would pin the current interval forever, so it is not offered."""
    input_fields = get_input_fields({CONF_ELEMENT_TYPE: ELEMENT_TYPE})
    schema_info = get_input_field_schema_info(ELEMENT_TYPE, input_fields)

    kinds = get_schema_value_kinds(schema_info[SECTION_TRIP][CONF_CONNECTED].value_type)

    assert kinds == frozenset({VALUE_TYPE_ENTITY, VALUE_TYPE_NONE})


@pytest.mark.parametrize(
    ("section", "field"),
    [(SECTION_PUBLIC_CHARGING, CONF_PUBLIC_CHARGING_PRICE), (SECTION_TRIP, CONF_RESERVE_PRICE)],
)
def test_penalty_prices_cannot_be_negative(section: str, field: str) -> None:
    """Penalty price inputs are bounded below by zero so the optimization stays bounded."""
    field_info = get_input_fields(ELEMENT_TYPE)[section][field]

    assert field_info.entity_description.native_min_value == 0.0
