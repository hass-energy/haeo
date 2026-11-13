"""Tests for checking and converting source values against an input field's unit."""

import pytest

from custom_components.haeo.core.data.util.field_units import (
    check_source_unit,
    field_unit_label,
    field_unit_spec,
    has_field_unit,
    to_field_unit,
)
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.model.const import OutputType


@pytest.mark.parametrize(
    ("output_type", "expected"),
    [
        pytest.param(OutputType.POWER, True, id="power"),
        pytest.param(OutputType.PRICE, True, id="price"),
        pytest.param(OutputType.AVAILABILITY, False, id="availability"),
        pytest.param(OutputType.STATUS, False, id="status"),
    ],
)
def test_has_field_unit(output_type: OutputType, *, expected: bool) -> None:
    """Fields measuring a quantity carry a unit; flags and statuses do not."""
    assert has_field_unit(output_type) is expected


@pytest.mark.parametrize(
    ("base_unit", "output_type"),
    [
        pytest.param("kW", OutputType.POWER_LIMIT, id="power"),
        pytest.param("AUD/kWh", OutputType.PRICE, id="price_in_any_currency"),
        pytest.param("%", OutputType.STATE_OF_CHARGE, id="percent"),
        pytest.param(None, OutputType.POWER, id="source_without_unit"),
        pytest.param("kWh", OutputType.AVAILABILITY, id="field_without_unit"),
    ],
)
def test_check_source_unit_accepts_fitting_units(base_unit: str | None, output_type: OutputType) -> None:
    """A source in the field's unit, a source stating no unit, or a field without one passes."""
    check_source_unit(base_unit, output_type)


@pytest.mark.parametrize(
    ("base_unit", "output_type"),
    [
        pytest.param("kWh", OutputType.POWER, id="energy_for_power"),
        pytest.param("kW", OutputType.PRICE, id="power_for_price"),
        pytest.param("BTU/h", OutputType.POWER, id="unconvertible_power"),
    ],
)
def test_check_source_unit_rejects_units_that_do_not_fit(base_unit: str, output_type: OutputType) -> None:
    """A source whose unit does not convert to the field's unit is rejected."""
    with pytest.raises(InputError) as err:
        check_source_unit(base_unit, output_type)

    assert err.value.translation_key == "input_unit_incompatible"
    assert err.value.translation_placeholders["unit"] == base_unit


@pytest.mark.parametrize(
    ("output_type", "expected"),
    [
        pytest.param(OutputType.POWER, "W, kW, MW, GW", id="power"),
        pytest.param(
            OutputType.ENERGY_PER_DISTANCE, "Wh/km, kWh/km, kWh/100km, km/kWh, mi/kWh", id="energy_per_distance"
        ),
        pytest.param(OutputType.STATE_OF_CHARGE, "%", id="percent"),
    ],
)
def test_check_source_unit_names_the_units_a_source_can_state(output_type: OutputType, expected: str) -> None:
    """A rejected source is told every unit the field converts from, not only the unit HAEO works in."""
    with pytest.raises(InputError) as err:
        check_source_unit("furlongs", output_type)

    assert err.value.translation_placeholders["expected"] == expected


@pytest.mark.parametrize(
    ("value", "unit", "output_type", "expected"),
    [
        pytest.param(500.0, "W", OutputType.POWER, 0.5, id="watts_to_kw"),
        pytest.param(40.0, "kWh", OutputType.ENERGY, 40.0, id="kwh"),
        pytest.param(90.0, "min", OutputType.DURATION, 1.5, id="minutes_to_hours"),
        pytest.param(150.0, "€/MWh", OutputType.PRICE, 0.15, id="price_per_mwh"),
        pytest.param(26.5, "c/kWh", OutputType.PRICE, 0.265, id="cents_per_kwh"),
        pytest.param(10.0, "mi", OutputType.DISTANCE, 16.09344, id="miles_to_km"),
        pytest.param(5.0, "km/kWh", OutputType.ENERGY_PER_DISTANCE, 0.2, id="reciprocal_efficiency"),
        pytest.param(1.0, None, OutputType.AVAILABILITY, 1.0, id="bare_number_without_field_unit"),
    ],
)
def test_to_field_unit_converts(value: float, unit: str | None, output_type: OutputType, expected: float) -> None:
    """A value typed with a unit converts to the field's unit."""
    assert to_field_unit(value, unit, output_type) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("unit", "output_type"),
    [
        pytest.param(None, OutputType.POWER, id="bare_number"),
        pytest.param("kWh", OutputType.POWER, id="wrong_kind"),
        pytest.param("furlongs", OutputType.POWER, id="unknown_unit"),
        pytest.param("kW", OutputType.AVAILABILITY, id="unit_without_field_unit"),
    ],
)
def test_to_field_unit_rejects_values_it_cannot_convert(unit: str | None, output_type: OutputType) -> None:
    """A bare number is never taken to be in HAEO's units, and a unit must convert to the field's."""
    assert to_field_unit(5.0, unit, output_type) is None


def test_to_field_unit_rejects_zero_in_a_reciprocal_unit() -> None:
    """Zero km/kWh has no finite energy per distance, so the value cannot be used."""
    assert to_field_unit(0.0, "km/kWh", OutputType.ENERGY_PER_DISTANCE) is None


@pytest.mark.parametrize(
    ("output_type", "expected"),
    [
        pytest.param(OutputType.ENERGY, None, id="energy_cannot_be_negative"),
        pytest.param(OutputType.PRICE, -0.05, id="price_can_be_negative"),
    ],
)
def test_to_field_unit_rejects_negative_quantities(output_type: OutputType, expected: float | None) -> None:
    """A quantity that cannot be negative rejects a negative value; a price takes one."""
    unit = "$/kWh" if output_type == OutputType.PRICE else "kWh"

    assert to_field_unit(-0.05, unit, output_type) == expected


def test_field_unit_label() -> None:
    """A field's unit is named to users, and a field without one has no label."""
    assert field_unit_label(OutputType.POWER) == "kW"
    assert field_unit_label(OutputType.AVAILABILITY) is None


def test_field_unit_spec() -> None:
    """A field's unit is the one its sources' values must convert to, and a field without one has none."""
    assert field_unit_spec(OutputType.POWER) == "kW"
    assert field_unit_spec(OutputType.AVAILABILITY) is None
