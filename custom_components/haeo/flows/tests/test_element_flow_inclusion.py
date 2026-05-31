"""Tests for config flow entity inclusion map unit filtering."""

from homeassistant.components.number import NumberEntityDescription
import pytest

from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.model.const import OutputType
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
