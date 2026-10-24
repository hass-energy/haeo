"""Tests for the shared element flow helpers."""

from types import MappingProxyType

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.const import UnitOfEnergyDistance, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util.unit_conversion import DistanceConverter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import CONF_SOURCE, CONF_TARGET, SECTION_ENDPOINTS
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ROLE
from custom_components.haeo.core.schema.elements.policy import CONF_PRICE, CONF_RULES
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint, MeterFieldHint
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.core.units import UnitOfMeasurement, convert_to_base_unit
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows import HUB_SECTION_ADVANCED
from custom_components.haeo.flows.conftest import create_flow
from custom_components.haeo.flows.element_flow import build_inclusion_map


def _field(field_name: str, output_type: OutputType) -> InputFieldInfo[NumberEntityDescription]:
    return InputFieldInfo(
        field_name=field_name,
        entity_description=NumberEntityDescription(key=field_name, name=field_name),
        output_type=output_type,
    )


@pytest.mark.parametrize(
    ("output_type", "unit", "other_units"),
    [
        *(pytest.param(OutputType.POWER_LIMIT, unit, ["kWh"], id=f"power_{unit}") for unit in ("W", "kW", "MW")),
        *(pytest.param(OutputType.ENERGY, unit, ["kW"], id=f"energy_{unit}") for unit in ("Wh", "kWh", "MWh", "GWh")),
        *(
            pytest.param(OutputType.PRICE, unit, ["kW"], id=f"price_{unit}")
            for unit in ("$/kWh", "€/MWh", "AUD/Wh", "£/GWh")
        ),
        *(
            pytest.param(OutputType.DURATION, unit, ["ms", "kW"], id=f"duration_{unit}")
            for unit in ("s", "min", "h", "d")
        ),
    ],
)
def test_build_inclusion_map_includes_compatible_units(
    output_type: OutputType, unit: str, other_units: list[str]
) -> None:
    """A field accepts any unit that converts to its own, in any currency for prices, and no other unit."""
    entity_metadata = [
        EntityMetadata(entity_id="sensor.compatible", unit_of_measurement=unit),
        *(
            EntityMetadata(entity_id=f"sensor.other_{index}", unit_of_measurement=other_unit)
            for index, other_unit in enumerate(other_units)
        ),
    ]
    inclusion_map = build_inclusion_map({"field": _field("field", output_type)}, entity_metadata)

    assert inclusion_map["field"] == ["sensor.compatible"]


@pytest.mark.parametrize(
    ("time_series", "expected"),
    [
        pytest.param(True, ["sensor.price", "calendar.demand"], id="forecast_field"),
        pytest.param(False, ["sensor.price"], id="scalar_field"),
    ],
)
def test_build_inclusion_map_includes_calendars_for_forecast_fields(*, time_series: bool, expected: list[str]) -> None:
    """A number forecast field also includes every calendar, read as a forecast of its events' numbers."""
    entity_metadata = [
        EntityMetadata(entity_id="sensor.price", unit_of_measurement="$/kWh"),
        EntityMetadata(entity_id="calendar.demand", unit_of_measurement=None),
    ]
    field = InputFieldInfo(
        field_name="price",
        entity_description=NumberEntityDescription(key="price", name="price"),
        output_type=OutputType.PRICE,
        time_series=time_series,
    )

    assert build_inclusion_map({"price": field}, entity_metadata)["price"] == expected


def test_build_inclusion_map_offers_only_calendars_for_calendar_fields() -> None:
    """A field feeding calendar inputs includes only calendars."""
    entity_metadata = [
        EntityMetadata(entity_id="sensor.energy", unit_of_measurement="kWh"),
        EntityMetadata(entity_id="calendar.trips", unit_of_measurement=None),
    ]
    due = InputFieldInfo(
        field_name="trip_due",
        entity_description=NumberEntityDescription(key="trip_due", name="trip_due"),
        output_type=OutputType.ENERGY,
        calendar=CalendarFieldHint(projection="event_due"),
    )
    field = InputFieldInfo(
        field_name="trip_calendar",
        entity_description=NumberEntityDescription(key="trip_calendar", name="trip_calendar"),
        output_type=OutputType.ENERGY,
        outputs={"trip_due": due},
    )

    assert build_inclusion_map({"trip_calendar": field}, entity_metadata)["trip_calendar"] == ["calendar.trips"]


@pytest.mark.parametrize("unit", list(UnitOfLength))
def test_selectable_distance_units_convert_to_kilometers(unit: UnitOfLength) -> None:
    """Every length unit a distance field accepts converts to kilometers like Home Assistant does."""
    entity_metadata = [EntityMetadata(entity_id="sensor.odometer", unit_of_measurement=unit)]
    inclusion_map = build_inclusion_map({"odometer": _field("odometer", OutputType.DISTANCE)}, entity_metadata)
    assert inclusion_map["odometer"] == ["sensor.odometer"]

    value, base_unit, _ = convert_to_base_unit(123.0, unit, SensorDeviceClass.DISTANCE)

    assert base_unit == UnitOfMeasurement.KILOMETER
    assert value == pytest.approx(DistanceConverter.convert(123.0, unit, UnitOfLength.KILOMETERS))


@pytest.mark.parametrize(
    ("unit", "included"),
    [
        ("kWh/km", True),
        (UnitOfEnergyDistance.KILO_WATT_HOUR_PER_100_KM, True),
        (UnitOfEnergyDistance.WATT_HOUR_PER_KM, True),
        (UnitOfEnergyDistance.MILES_PER_KILO_WATT_HOUR, False),
        (UnitOfEnergyDistance.KM_PER_KILO_WATT_HOUR, False),
        ("kWh", False),
    ],
)
def test_energy_per_distance_accepts_only_convertible_consumption_units(unit: str, *, included: bool) -> None:
    """Energy per distance fields accept consumption units that convert to kWh/km."""
    entity_metadata = [EntityMetadata(entity_id="sensor.consumption", unit_of_measurement=unit)]
    inclusion_map = build_inclusion_map(
        {"energy_per_distance": _field("energy_per_distance", OutputType.ENERGY_PER_DISTANCE)},
        entity_metadata,
    )

    assert (inclusion_map["energy_per_distance"] == ["sensor.consumption"]) is included


def test_build_inclusion_map_offers_only_running_totals_for_meter_fields() -> None:
    """A meter field only includes unit-compatible entities the recorder keeps a running total for."""
    entity_metadata = [
        EntityMetadata(entity_id="sensor.pump_energy", unit_of_measurement="kWh", state_class="total_increasing"),
        EntityMetadata(entity_id="sensor.pump_energy_today", unit_of_measurement="kWh", state_class="total"),
        EntityMetadata(entity_id="sensor.battery_stored", unit_of_measurement="kWh", state_class="measurement"),
        EntityMetadata(entity_id="sensor.pump_estimate", unit_of_measurement="kWh"),
    ]
    field = InputFieldInfo(
        field_name="energy_meter",
        entity_description=NumberEntityDescription(key="energy_meter", name="energy_meter"),
        output_type=OutputType.ENERGY,
        meter=MeterFieldHint(since="window_calendar"),
    )

    assert build_inclusion_map({"energy_meter": field}, entity_metadata)["energy_meter"] == [
        "sensor.pump_energy",
        "sensor.pump_energy_today",
    ]


def _set_advanced_mode(hass: HomeAssistant, hub_entry: MockConfigEntry, *, advanced_mode: bool) -> None:
    hass.config_entries.async_update_entry(
        hub_entry,
        data={**hub_entry.data, HUB_SECTION_ADVANCED: {CONF_ADVANCED_MODE: advanced_mode}},
    )


@pytest.mark.parametrize("advanced_mode", [False, True], ids=["standard", "advanced"])
@pytest.mark.parametrize(
    ("node_type", "inverter_type"),
    [
        pytest.param(ElementType.NODE, ElementType.INVERTER, id="enum"),
        # Subentry data reloaded after a restart holds plain strings
        pytest.param("node", "inverter", id="deserialized_string"),
    ],
)
async def test_participant_names_resolve_element_type(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    node_type: str,
    inverter_type: str,
    *,
    advanced_mode: bool,
) -> None:
    """Participant names resolve whether element_type is an ElementType or the string it deserializes to."""
    _set_advanced_mode(hass, hub_entry, advanced_mode=advanced_mode)
    add_participant(hass, hub_entry, "Switchboard", node_type)
    add_participant(hass, hub_entry, "Inverter", inverter_type)

    flow = create_flow(hass, hub_entry, ElementType.INVERTER)

    assert "Switchboard" in flow._get_participant_names()


@pytest.mark.parametrize(
    ("advanced_mode", "expected"),
    [
        pytest.param(False, ["Inverter", "Junction", "Node"], id="standard"),
        pytest.param(True, ["Battery Section", "Inverter", "Junction", "Node"], id="advanced"),
    ],
)
async def test_participant_names_exclude_elements_with_own_connections(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    advanced_mode: bool,
    expected: list[str],
) -> None:
    """Grid, battery, solar, and load are never endpoints, even in advanced mode."""
    _set_advanced_mode(hass, hub_entry, advanced_mode=advanced_mode)
    for element_type in ElementType:
        add_participant(hass, hub_entry, element_type.replace("_", " ").title(), element_type)

    flow = create_flow(hass, hub_entry, ElementType.CONNECTION)

    assert flow._get_participant_names() == expected


def _add_subentry(hass: HomeAssistant, hub_entry: MockConfigEntry, data: dict[str, object]) -> ConfigSubentry:
    subentry = ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=str(data[CONF_ELEMENT_TYPE]),
        title=str(data[CONF_NAME]),
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


async def test_renaming_an_element_renames_it_in_every_element_that_names_it(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Connections, connected elements, and policy rules follow an element to its new name."""
    bus = _add_subentry(
        hass,
        hub_entry,
        {
            CONF_ELEMENT_TYPE: ElementType.NODE,
            CONF_NAME: "Bus",
            SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
        },
    )
    add_participant(hass, hub_entry, "Other", ElementType.NODE)
    link = _add_subentry(
        hass,
        hub_entry,
        {
            CONF_ELEMENT_TYPE: ElementType.CONNECTION,
            CONF_NAME: "Link",
            SECTION_ENDPOINTS: {CONF_SOURCE: as_connection_target("Bus"), CONF_TARGET: as_connection_target("Other")},
        },
    )
    load = _add_subentry(
        hass,
        hub_entry,
        {CONF_ELEMENT_TYPE: ElementType.LOAD, CONF_NAME: "House", CONF_CONNECTION: as_connection_target("Bus")},
    )
    policy = _add_subentry(
        hass,
        hub_entry,
        {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_NAME: "Policies",
            CONF_RULES: [{CONF_NAME: "Bus out", CONF_SOURCE: ["Bus", "Other"], CONF_PRICE: 0.1}],
        },
    )

    form = await hass.config_entries.subentries.async_init(
        (hub_entry.entry_id, ElementType.NODE),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": bus.subentry_id},
    )
    result = await hass.config_entries.subentries.async_configure(
        form["flow_id"],
        {CONF_NAME: "Main Bus", SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False}},
    )

    assert result.get("type") == FlowResultType.ABORT
    subentries = hub_entry.subentries
    assert subentries[bus.subentry_id].title == "Main Bus"
    assert subentries[link.subentry_id].data[SECTION_ENDPOINTS] == {
        CONF_SOURCE: as_connection_target("Main Bus"),
        CONF_TARGET: as_connection_target("Other"),
    }
    assert subentries[load.subentry_id].data[CONF_CONNECTION] == as_connection_target("Main Bus")
    assert subentries[policy.subentry_id].data[CONF_RULES] == [
        {CONF_NAME: "Bus out", CONF_SOURCE: ["Main Bus", "Other"], CONF_PRICE: 0.1}
    ]
