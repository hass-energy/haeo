"""Tests for config flow entity inclusion map unit filtering."""

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergyDistance, UnitOfLength
from homeassistant.util.unit_conversion import DistanceConverter
import pytest

from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.units import UnitOfMeasurement, convert_to_base_unit
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
