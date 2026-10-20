"""Tests for EV element config flow."""

from types import MappingProxyType
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    VALUE_TYPE_ENTITY,
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
    CONF_PUBLIC_CHARGING_PRICE,
    CONF_TRIP_CALENDAR,
    ELEMENT_TYPE,
    SECTION_CHARGING,
    SECTION_PUBLIC_CHARGING,
    SECTION_TRIP,
    SECTION_VEHICLE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION, SECTION_EFFICIENCY, SECTION_POWER_LIMITS
from custom_components.haeo.elements import get_input_field_schema_info, get_input_fields
from custom_components.haeo.elements.input_fields import is_number_field_info
from custom_components.haeo.flows.conftest import create_flow
from custom_components.haeo.flows.field_schema import CHOICE_ENTITY
from custom_components.haeo.flows.on_off_states import (
    CONF_OFF_STATES,
    CONF_ON_STATES,
    STEP_STATES,
    async_state_suggestions,
)


def _user_input(trip: dict[str, object] | None = None) -> dict[str, object]:
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
            CONF_CONNECTED: ["binary_sensor.ev_plugged_in"],
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
            CONF_TRIP_CALENDAR: ["calendar.ev_trips"],
            CONF_ODOMETER: ["sensor.ev_odometer"],
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_TRIP][CONF_TRIP_CALENDAR] == as_entity_value(["calendar.ev_trips"])
    assert data[SECTION_CHARGING][CONF_CONNECTED] == as_entity_value(["binary_sensor.ev_plugged_in"])
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
        SECTION_CHARGING: {
            CONF_MAX_CHARGE_RATE: as_constant_value(7.4),
            CONF_CONNECTED: as_entity_value(["binary_sensor.ev_plugged_in"]),
        },
        SECTION_TRIP: {
            CONF_TRIP_CALENDAR: as_entity_value(["calendar.ev_trips"]),
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
    assert defaults[SECTION_TRIP][CONF_TRIP_CALENDAR] == ["calendar.ev_trips"]


def test_plugged_in_field_requires_a_live_sensor() -> None:
    """The plugged-in sensor is required and takes only an entity: a constant would pin the current interval."""
    input_fields = get_input_fields({CONF_ELEMENT_TYPE: ELEMENT_TYPE})
    schema_info = get_input_field_schema_info(ELEMENT_TYPE, input_fields)

    kinds = get_schema_value_kinds(schema_info[SECTION_CHARGING][CONF_CONNECTED].value_type)

    assert kinds == frozenset({VALUE_TYPE_ENTITY})


def test_public_charging_price_cannot_be_negative() -> None:
    """The public charging price prices trip shortfalls, so it is bounded below by zero to keep the plan bounded."""
    field_info = get_input_fields(ELEMENT_TYPE)[SECTION_PUBLIC_CHARGING][CONF_PUBLIC_CHARGING_PRICE]

    assert is_number_field_info(field_info)
    assert field_info.entity_description.native_min_value == 0.0


async def test_plugged_in_entity_picker_offers_binary_sensors(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """The plugged-in picker offers binary sensors and input booleans alongside numeric entities."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=None)

    sections = {marker.schema: section for marker, section in result["data_schema"].schema.items()}
    charging_fields = {marker.schema: selector for marker, selector in sections[SECTION_CHARGING].schema.schema.items()}
    entity_choice = charging_fields[CONF_CONNECTED].config["choices"][CHOICE_ENTITY]
    domains = entity_choice["selector"]["entity"]["domain"]

    assert {"binary_sensor", "input_boolean"} <= set(domains)


CHARGER = "sensor.charger_status"


def _charger_input() -> dict[str, object]:
    """Build EV user input whose plugged-in sensor is a charger reporting words."""
    user_input = _user_input()
    user_input[SECTION_CHARGING] = {CONF_MAX_CHARGE_RATE: 7.4, CONF_CONNECTED: [CHARGER]}
    return user_input


async def test_plugged_in_sensor_reporting_words_asks_for_its_states(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """A plugged-in sensor reporting words leads to a step choosing its states before the EV is saved."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    hass.states.async_set(CHARGER, "Idle", {"options": ["Idle", "Charging", "Fault"]})
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test EV", "data": {}})

    result = await flow.async_step_user(user_input=_charger_input())

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == STEP_STATES
    selector = result["data_schema"].schema[next(iter(result["data_schema"].schema))]
    assert selector.config["options"] == ["Idle", "Charging", "Fault"]
    flow.async_create_entry.assert_not_called()

    result = await flow.async_step_states({CONF_OFF_STATES: ["Idle"]})

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_CHARGING][CONF_CONNECTED] == as_entity_value([CHARGER], off_states=["Idle"])


async def test_states_step_needs_at_least_one_state(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Choosing no states at all is rejected, as every state would then have no reading."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    hass.states.async_set(CHARGER, "Charging")
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    await flow.async_step_user(user_input=_charger_input())

    result = await flow.async_step_states({CONF_ON_STATES: [], CONF_OFF_STATES: []})

    assert result.get("step_id") == STEP_STATES
    assert result.get("errors") == {"base": "states_required"}


@pytest.mark.parametrize(
    ("entity_id", "state"),
    [
        pytest.param("binary_sensor.ev_plugged_in", "on", id="binary_sensor"),
        pytest.param("sensor.ev_plugged_in", "1", id="numeric_sensor"),
    ],
)
async def test_plugged_in_sensor_reading_on_or_off_saves_directly(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    entity_id: str,
    state: str,
) -> None:
    """A plugged-in sensor that already reads as on or off needs no states."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    hass.states.async_set(entity_id, state)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test EV", "data": {}})
    user_input = _user_input()
    user_input[SECTION_CHARGING] = {CONF_MAX_CHARGE_RATE: 7.4, CONF_CONNECTED: [entity_id]}

    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY


async def test_states_suggest_what_the_recorder_saw(hass: HomeAssistant) -> None:
    """A sensor without listed options suggests the states the recorder saw, then its current state."""
    hass.config.components.add("recorder")
    hass.states.async_set(CHARGER, "Idle")
    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(return_value=["Charging", "Idle", "unavailable", "Ended"])

    with patch("custom_components.haeo.flows.on_off_states.get_instance", return_value=recorder):
        suggestions = await async_state_suggestions(hass, [CHARGER])

    assert suggestions == ["Charging", "Idle", "Ended"]


async def test_reconfigure_suggests_the_stored_states(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfiguring an EV suggests the states it stored."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    hass.states.async_set(CHARGER, "Idle")
    from custom_components.haeo.core.schema import as_connection_target  # noqa: PLC0415

    existing_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: "Test EV",
                CONF_CONNECTION: as_connection_target("TestNode"),
                SECTION_VEHICLE: {
                    CONF_CAPACITY: as_constant_value(60.0),
                    CONF_ENERGY_PER_DISTANCE: as_constant_value(0.15),
                    CONF_CURRENT_SOC: as_entity_value(["sensor.ev_soc"]),
                },
                SECTION_CHARGING: {
                    CONF_MAX_CHARGE_RATE: as_constant_value(7.4),
                    CONF_CONNECTED: as_entity_value([CHARGER], off_states=["Idle"]),
                },
                SECTION_TRIP: {},
                SECTION_PUBLIC_CHARGING: {},
                SECTION_POWER_LIMITS: {},
                SECTION_EFFICIENCY: {},
            }
        ),
        subentry_type=ELEMENT_TYPE,
        title="Test EV",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    result = await flow.async_step_reconfigure(user_input=_charger_input())

    assert result.get("step_id") == STEP_STATES
    suggested = {
        marker.schema: (marker.description or {}).get("suggested_value") for marker in result["data_schema"].schema
    }
    assert suggested == {CONF_ON_STATES: [], CONF_OFF_STATES: ["Idle"]}
