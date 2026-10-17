"""Tests for config flow entity inclusion map unit filtering."""

from homeassistant.components.number import NumberEntityDescription
import pytest

from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.element_flow import build_inclusion_map


def _field(field_name: str, output_type: OutputType) -> InputFieldInfo[NumberEntityDescription]:
    return InputFieldInfo(
        field_name=field_name,
        entity_description=NumberEntityDescription(key=field_name, name=field_name),
        output_type=output_type,
    )


@pytest.mark.parametrize(
    ("entity_id", "unit"),
    [
        ("sensor.power_w", "W"),
        ("sensor.power_kw", "kW"),
        ("sensor.power_mw", "MW"),
    ],
)
def test_build_inclusion_map_includes_compatible_power_units(entity_id: str, unit: str) -> None:
    """Power fields accept any Home Assistant power unit."""
    entity_metadata = [
        EntityMetadata(entity_id=entity_id, unit_of_measurement=unit),
        EntityMetadata(entity_id="sensor.energy", unit_of_measurement="kWh"),
    ]
    inclusion_map = build_inclusion_map({"max_power": _field("max_power", OutputType.POWER_LIMIT)}, entity_metadata)

    assert inclusion_map["max_power"] == [entity_id]


@pytest.mark.parametrize(
    ("entity_id", "unit"),
    [
        ("sensor.energy_wh", "Wh"),
        ("sensor.energy_kwh", "kWh"),
        ("sensor.energy_mwh", "MWh"),
        ("sensor.energy_gwh", "GWh"),
    ],
)
def test_build_inclusion_map_includes_compatible_energy_units(entity_id: str, unit: str) -> None:
    """Energy fields accept any Home Assistant energy unit."""
    entity_metadata = [
        EntityMetadata(entity_id=entity_id, unit_of_measurement=unit),
        EntityMetadata(entity_id="sensor.power", unit_of_measurement="kW"),
    ]
    inclusion_map = build_inclusion_map({"capacity": _field("capacity", OutputType.ENERGY)}, entity_metadata)

    assert inclusion_map["capacity"] == [entity_id]


@pytest.mark.parametrize(
    ("entity_id", "unit"),
    [
        ("sensor.price_kwh", "$/kWh"),
        ("sensor.price_mwh", "€/MWh"),
        ("sensor.price_wh", "AUD/Wh"),
        ("sensor.price_gwh", "£/GWh"),
    ],
)
def test_build_inclusion_map_includes_compatible_price_units(entity_id: str, unit: str) -> None:
    """Price fields accept any currency paired with a supported energy denominator."""
    entity_metadata = [
        EntityMetadata(entity_id=entity_id, unit_of_measurement=unit),
        EntityMetadata(entity_id="sensor.power", unit_of_measurement="kW"),
    ]
    inclusion_map = build_inclusion_map({"price": _field("price", OutputType.PRICE)}, entity_metadata)

    assert inclusion_map["price"] == [entity_id]


@pytest.mark.parametrize(
    ("entity_id", "unit"),
    [
        ("sensor.duration_s", "s"),
        ("sensor.duration_min", "min"),
        ("sensor.duration_h", "h"),
        ("sensor.duration_d", "d"),
    ],
)
def test_build_inclusion_map_includes_compatible_duration_units(entity_id: str, unit: str) -> None:
    """Duration fields accept the time units HAEO converts to hours."""
    entity_metadata = [
        EntityMetadata(entity_id=entity_id, unit_of_measurement=unit),
        EntityMetadata(entity_id="sensor.duration_ms", unit_of_measurement="ms"),
        EntityMetadata(entity_id="sensor.power", unit_of_measurement="kW"),
    ]
    inclusion_map = build_inclusion_map({"window": _field("window", OutputType.DURATION)}, entity_metadata)

    assert inclusion_map["window"] == [entity_id]


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
        calendar=CalendarFieldHint(projection="window_due"),
    )
    field = InputFieldInfo(
        field_name="trip_calendar",
        entity_description=NumberEntityDescription(key="trip_calendar", name="trip_calendar"),
        output_type=OutputType.ENERGY,
        outputs={"trip_due": due},
    )

    assert build_inclusion_map({"trip_calendar": field}, entity_metadata)["trip_calendar"] == ["calendar.trips"]
