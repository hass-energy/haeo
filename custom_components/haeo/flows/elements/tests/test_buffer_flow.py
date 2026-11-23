"""Tests for the buffer element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import ChooseSelector, SelectSelector
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from conftest import add_participant
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import (
    BUFFER_KINDS,
    CONF_GENERATION,
    CONF_KIND,
    CONF_LEVEL,
    CONF_LOADS,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    ELEMENT_TYPE,
    KIND_HEADROOM,
    KIND_RESERVE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)
from custom_components.haeo.flows.conftest import create_flow
from custom_components.haeo.flows.field_schema import CHOICE_ENTITY, CHOICE_NONE
from custom_components.haeo.unique_id import element_unique_id

ELEMENTS = (
    ("House", ElementType.LOAD),
    ("Pool pump", ElementType.DEFERRABLE_LOAD),
    ("Car", ElementType.EV),
    ("Solar", ElementType.SOLAR),
    ("Battery", ElementType.BATTERY),
    ("Section", ElementType.BATTERY_SECTION),
    ("Grid", ElementType.GRID),
    ("Bus", ElementType.NODE),
)


def _add_elements(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Add every kind of element, each with a power sensor, and power sensors from outside the hub."""
    for name, element_type in ELEMENTS:
        subentry = add_participant(hass, hub_entry, name, element_type)
        entity = er.async_get(hass).async_get_or_create(
            "sensor",
            DOMAIN,
            element_unique_id(hub_entry.entry_id, subentry.subentry_id, "power"),
            config_entry=hub_entry,
            config_subentry_id=subentry.subentry_id,
            suggested_object_id=f"{name}_power",
        )
        hass.states.async_set(entity.entity_id, "1.0", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.load_p90", "1.0", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.solar_p10", "1.0", {"unit_of_measurement": "kW"})


def _offered_entities(schema: vol.Schema, key: str) -> list[str]:
    """Return the entities a participants field offers to pick."""
    selector = _section_field(schema, SECTION_PARTICIPANTS, key)
    assert isinstance(selector, ChooseSelector)
    return list(selector.config["choices"][CHOICE_ENTITY]["selector"]["entity"]["include_entities"])


def _user_input(kind: str = KIND_RESERVE, level: object = 20.0, **participants: object) -> dict[str, object]:
    return {
        CONF_NAME: "Backup",
        CONF_KIND: kind,
        SECTION_PARTICIPANTS: participants,
        SECTION_REQUIREMENT: {CONF_WINDOW: 12.0, CONF_LEVEL: level},
        SECTION_PRICING: {CONF_SHORTFALL_COST: 0.05},
    }


def _schema_key(schema: vol.Schema, key: str) -> vol.Marker:
    """Return the schema marker for a top-level form field."""
    marker: vol.Marker = next(field for field in schema.schema if field == key)
    return marker


def _section_fields(schema: vol.Schema, section_key: str) -> dict[vol.Marker, object]:
    """Return the fields of a form section by their markers."""
    form_section = schema.schema[_schema_key(schema, section_key)]
    assert isinstance(form_section, section)
    return dict(form_section.schema.schema)


def _section_field(schema: vol.Schema, section_key: str, key: str) -> object:
    """Return the selector of one field in a form section."""
    return next(value for field, value in _section_fields(schema, section_key).items() if field == key)


def _section_options(schema: vol.Schema, section_key: str) -> dict[str, list[str]]:
    """Return the options each select selector in a form section offers."""
    return {
        str(key): list(selector.config["options"])
        for key, selector in _section_fields(schema, section_key).items()
        if isinstance(selector, SelectSelector)
    }


def _add_buffer(hass: HomeAssistant, hub_entry: MockConfigEntry, data: dict[str, object]) -> ConfigSubentry:
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE, **data}),
        subentry_type=ELEMENT_TYPE,
        title=str(data[CONF_NAME]),
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


async def test_participants_offer_the_sensors_and_elements_that_fit_each_role(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Loads and generation offer power sensors and the sensors of the elements that can take the role.

    Deferrable loads and EVs count as loads, and batteries, battery sections and EVs hold the buffer.
    """
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=None)

    schema = result["data_schema"]
    assert sorted(_offered_entities(schema, CONF_LOADS)) == [
        "sensor.car_power",
        "sensor.house_power",
        "sensor.load_p90",
        "sensor.pool_pump_power",
        "sensor.solar_p10",
    ]
    assert sorted(_offered_entities(schema, CONF_GENERATION)) == [
        "sensor.load_p90",
        "sensor.solar_p10",
        "sensor.solar_power",
    ]
    assert _section_options(schema, SECTION_PARTICIPANTS) == {CONF_STORAGE: ["Car", "Battery", "Section"]}


async def test_storage_never_offers_buffers(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Other buffers are never offered to hold a buffer."""
    _add_elements(hass, hub_entry)
    _add_buffer(hass, hub_entry, {CONF_NAME: "Other", CONF_KIND: KIND_RESERVE})
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=None)

    assert "Other" not in _section_options(result["data_schema"], SECTION_PARTICIPANTS)[CONF_STORAGE]


async def test_kind_select_offers_both_kinds_and_defaults_to_reserve(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """A new buffer offers reserve and headroom, with reserve suggested."""
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=None)

    schema = result["data_schema"]
    kind_key = _schema_key(schema, CONF_KIND)
    selector = schema.schema[kind_key]
    assert isinstance(selector, SelectSelector)
    assert list(selector.config["options"]) == list(BUFFER_KINDS)
    assert selector.config["translation_key"] == "buffer_kind"
    assert kind_key.description == {"suggested_value": KIND_RESERVE}


async def test_level_offers_none_choice(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """The level is optional, so its selector offers the None choice."""
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=None)

    level = _section_field(result["data_schema"], SECTION_REQUIREMENT, CONF_LEVEL)
    window = _section_field(result["data_schema"], SECTION_REQUIREMENT, CONF_WINDOW)
    assert isinstance(level, ChooseSelector)
    assert CHOICE_NONE in level.config["choices"]
    assert not isinstance(window, ChooseSelector) or CHOICE_NONE not in window.config["choices"]


@pytest.mark.parametrize("kind", BUFFER_KINDS)
async def test_buffer_needs_a_battery(hass: HomeAssistant, hub_entry: MockConfigEntry, kind: str) -> None:
    """A buffer without a battery to hold it is rejected."""
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    result = await flow.async_step_user(user_input=_user_input(kind, loads=["sensor.house_power"]))

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"base": "buffer_storage_required"}


@pytest.mark.parametrize(
    ("level", "expected_level"),
    [
        pytest.param(20.0, as_constant_value(20.0), id="constant"),
        pytest.param("", as_none_value(), id="none"),
    ],
)
async def test_create_stores_kind_and_level(
    hass: HomeAssistant, hub_entry: MockConfigEntry, level: object, expected_level: object
) -> None:
    """Creating a buffer stores its kind and its level, which may be left unset."""
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY})

    await flow.async_step_user(user_input=_user_input(KIND_HEADROOM, level, storage=["Battery"]))

    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[CONF_ELEMENT_TYPE] == ELEMENT_TYPE
    assert data[CONF_KIND] == KIND_HEADROOM
    assert data[SECTION_PARTICIPANTS] == {CONF_STORAGE: ["Battery"]}
    assert data[SECTION_REQUIREMENT] == {CONF_WINDOW: as_constant_value(12.0), CONF_LEVEL: expected_level}


async def test_create_stores_element_and_forecast_sensors_together(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """The sensors picked for loads and generation are stored as picked, whether they belong to an element or not."""
    _add_elements(hass, hub_entry)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY})

    await flow.async_step_user(
        user_input=_user_input(
            loads=["sensor.house_power", "sensor.load_p90"], generation=["sensor.solar_p10"], storage=["Battery"]
        )
    )

    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_PARTICIPANTS] == {
        CONF_LOADS: as_entity_value(["sensor.house_power", "sensor.load_p90"]),
        CONF_GENERATION: as_entity_value(["sensor.solar_p10"]),
        CONF_STORAGE: ["Battery"],
    }


async def test_reconfigure_keeps_kind_and_participants(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfiguring prefills the stored kind and participants and stores the inputs as schema values."""
    _add_elements(hass, hub_entry)
    subentry = _add_buffer(
        hass,
        hub_entry,
        {
            CONF_NAME: "Backup",
            CONF_KIND: KIND_HEADROOM,
            SECTION_PARTICIPANTS: {
                CONF_LOADS: as_entity_value(["sensor.house_power"]),
                CONF_STORAGE: ["Battery"],
            },
            SECTION_REQUIREMENT: {CONF_WINDOW: as_constant_value(6.0), CONF_LEVEL: as_constant_value(90.0)},
            SECTION_PRICING: {CONF_SHORTFALL_COST: as_constant_value(0.1)},
        },
    )
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT})

    form = await flow.async_step_reconfigure(user_input=None)
    schema = form["data_schema"]
    kind_key = _schema_key(schema, CONF_KIND)
    participants = _section_fields(schema, SECTION_PARTICIPANTS)
    await flow.async_step_reconfigure(
        user_input=_user_input(
            KIND_HEADROOM, loads=["sensor.house_power"], generation=["sensor.solar_power"], storage=["Battery"]
        )
    )

    assert kind_key.description == {"suggested_value": KIND_HEADROOM}
    suggested = {str(key): key.description for key in participants}
    assert suggested[CONF_LOADS] == {"suggested_value": ["sensor.house_power"]}
    assert suggested[CONF_STORAGE] == {"suggested_value": ["Battery"]}
    data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert data[CONF_KIND] == KIND_HEADROOM
    assert data[SECTION_PARTICIPANTS] == {
        CONF_LOADS: as_entity_value(["sensor.house_power"]),
        CONF_GENERATION: as_entity_value(["sensor.solar_power"]),
        CONF_STORAGE: ["Battery"],
    }
    assert data[SECTION_REQUIREMENT] == {CONF_WINDOW: as_constant_value(12.0), CONF_LEVEL: as_constant_value(20.0)}


async def test_reconfigure_shows_elements_named_directly_by_their_sensors(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """An element a buffer names directly is shown as its sensor, so saving the form keeps it."""
    _add_elements(hass, hub_entry)
    subentry = _add_buffer(
        hass,
        hub_entry,
        {
            CONF_NAME: "Backup",
            CONF_KIND: KIND_RESERVE,
            SECTION_PARTICIPANTS: {
                CONF_LOADS: {**as_entity_value(["sensor.load_p90"]), "elements": ["House"]},
                CONF_STORAGE: ["Battery"],
            },
            SECTION_REQUIREMENT: {CONF_WINDOW: as_constant_value(6.0)},
            SECTION_PRICING: {CONF_SHORTFALL_COST: as_constant_value(0.1)},
        },
    )
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    form = await flow.async_step_reconfigure(user_input=None)

    loads = next(key for key in _section_fields(form["data_schema"], SECTION_PARTICIPANTS) if key == CONF_LOADS)
    assert loads.description == {"suggested_value": ["sensor.load_p90", "sensor.house_power"]}
