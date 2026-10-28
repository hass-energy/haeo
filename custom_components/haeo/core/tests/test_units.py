"""Tests for base unit conversion utilities."""

import numpy as np
import pytest

from custom_components.haeo.core.units import (
    DeviceClass,
    UnitConversion,
    UnitOfMeasurement,
    base_unit_for_device_class,
    convert_to_base_unit,
    currency_symbol,
    localize_currency,
    price_currency,
)


@pytest.mark.parametrize(
    ("device_class", "expected"),
    [
        (DeviceClass.POWER, "kW"),
        (DeviceClass.ENERGY, "kWh"),
        (DeviceClass.ENERGY_STORAGE, "kWh"),
        (DeviceClass.DISTANCE, "km"),
        (DeviceClass.ENERGY_DISTANCE, "kWh/km"),
        (DeviceClass.DURATION, "h"),
        (None, None),
    ],
)
def test_base_unit_for_device_class(device_class: DeviceClass | None, expected: str | None) -> None:
    """Test base unit lookup for various device classes."""
    assert base_unit_for_device_class(device_class) == expected


@pytest.mark.parametrize(
    ("value", "unit", "device_class", "expected"),
    [
        # Power conversions
        (1000.0, UnitOfMeasurement.WATT, DeviceClass.POWER, 1.0),
        (1.0, UnitOfMeasurement.MEGA_WATT, DeviceClass.POWER, 1000.0),
        (1.0, UnitOfMeasurement.WATT, DeviceClass.POWER, 0.001),
        (1.0, UnitOfMeasurement.KILO_WATT, DeviceClass.POWER, 1.0),
        # Energy conversions
        (1000.0, UnitOfMeasurement.WATT_HOUR, DeviceClass.ENERGY, 1.0),
        (1.0, UnitOfMeasurement.MEGA_WATT_HOUR, DeviceClass.ENERGY, 1000.0),
        (5.0, UnitOfMeasurement.KILO_WATT_HOUR, DeviceClass.ENERGY, 5.0),
        # Energy storage uses same base unit as energy
        (1000.0, UnitOfMeasurement.WATT_HOUR, DeviceClass.ENERGY_STORAGE, 1.0),
        # Distance conversions
        (5.0, UnitOfMeasurement.MILE, DeviceClass.DISTANCE, 8.04672),
        (1500.0, UnitOfMeasurement.METER, DeviceClass.DISTANCE, 1.5),
        (12.0, UnitOfMeasurement.KILOMETER, DeviceClass.DISTANCE, 12.0),
        (10.0, UnitOfMeasurement.MILE, None, 16.09344),
        # Energy per distance conversions
        (18.0, UnitOfMeasurement.KILO_WATT_HOUR_PER_100_KILOMETER, DeviceClass.ENERGY_DISTANCE, 0.18),
        (180.0, UnitOfMeasurement.WATT_HOUR_PER_KILOMETER, None, 0.18),
        (0.2, UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER, DeviceClass.ENERGY_DISTANCE, 0.2),
        # Duration conversions to hours
        (90.0, UnitOfMeasurement.MINUTE, DeviceClass.DURATION, 1.5),
        (7200.0, UnitOfMeasurement.SECOND, DeviceClass.DURATION, 2.0),
        (1.0, UnitOfMeasurement.DAY, DeviceClass.DURATION, 24.0),
        (30.0, UnitOfMeasurement.MINUTE, None, 0.5),
        # No conversion when already in base unit
        (5.0, UnitOfMeasurement.KILO_WATT, DeviceClass.POWER, 5.0),
        # Fallback conversion when device_class is missing but unit is informative
        (100.0, UnitOfMeasurement.WATT, None, 0.1),
        (1000.0, UnitOfMeasurement.WATT_HOUR, None, 1.0),
        # No conversion for unconvertible units or unsupported device classes
        (25.0, UnitOfMeasurement.PERCENT, None, 25.0),
        (50.0, UnitOfMeasurement.PERCENT, None, 50.0),
        (75.0, UnitOfMeasurement.PERCENT, None, 75.0),
        # No conversion for device classes without HA converters
        (100.0, UnitOfMeasurement.DOLLAR_PER_KWH, DeviceClass.MONETARY, 100.0),
        # No conversion when from_unit is None
        (100.0, None, DeviceClass.POWER, 100.0),
    ],
)
def test_scale_factor(
    value: float,
    unit: UnitOfMeasurement | None,
    device_class: DeviceClass | None,
    expected: float,
) -> None:
    """Test unit conversion to base units for various device classes and units."""
    assert convert_to_base_unit(value, unit, device_class)[0] == pytest.approx(expected)


@pytest.mark.parametrize(
    ("value", "unit", "device_class", "expected"),
    [
        (
            1000.0,
            UnitOfMeasurement.WATT,
            DeviceClass.POWER,
            (1.0, UnitOfMeasurement.KILO_WATT, DeviceClass.POWER),
        ),
        (
            1000.0,
            UnitOfMeasurement.WATT,
            None,
            (1.0, UnitOfMeasurement.KILO_WATT, None),
        ),
        (
            1000.0,
            UnitOfMeasurement.WATT_HOUR,
            None,
            (1.0, UnitOfMeasurement.KILO_WATT_HOUR, None),
        ),
        (
            50.0,
            UnitOfMeasurement.PERCENT,
            None,
            (50.0, UnitOfMeasurement.PERCENT, None),
        ),
        (
            5.0,
            "mi",
            "distance",
            (8.04672, UnitOfMeasurement.KILOMETER, DeviceClass.DISTANCE),
        ),
        (
            18.0,
            "kWh/100km",
            "energy_distance",
            (0.18, UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER, DeviceClass.ENERGY_DISTANCE),
        ),
        # Spaces some integrations write inside a unit are ignored
        (
            18.0,
            "kWh/100 km",
            "energy_distance",
            (0.18, UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER, DeviceClass.ENERGY_DISTANCE),
        ),
        (
            1500.0,
            " W ",
            None,
            (1.5, UnitOfMeasurement.KILO_WATT, None),
        ),
        (
            12.0,
            "unknown_unit",
            None,
            (12.0, "unknown_unit", None),
        ),
        # Distance per energy units convert to their reciprocal, energy per distance
        (
            4.0,
            "mi/kWh",
            "energy_distance",
            (1 / (4.0 * 1.609344), UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER, DeviceClass.ENERGY_DISTANCE),
        ),
        (
            5.0,
            "km/kWh",
            None,
            (0.2, UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER, None),
        ),
        # A power sensor in a unit with no kW conversion is not reported as kW
        (
            3.0,
            "kVA",
            "power",
            (3.0, "kVA", DeviceClass.POWER),
        ),
    ],
)
def test_convert_to_base_unit(
    value: float,
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
    expected: tuple[float, UnitOfMeasurement | str | None, DeviceClass | None],
) -> None:
    """Convert value to base unit, parsing string unit/device_class if needed."""
    result_value, result_unit, result_device_class = convert_to_base_unit(value, unit, device_class)
    expected_value, expected_unit, expected_device_class = expected
    assert result_value == pytest.approx(expected_value)
    assert result_unit == expected_unit
    assert result_device_class == expected_device_class


@pytest.mark.parametrize(
    ("unit", "currency", "expected"),
    [
        ("$/kWh", "£", "£/kWh"),
        ("$/kWh", "$", "$/kWh"),
        ("$/kWh/h", "EUR", "EUR/kWh/h"),
        ("$/kW", "€", "€/kW"),
        ("$", "A$", "A$"),
        ("kW", "£", "kW"),
        ("%", "A$", "%"),
        (None, "£", None),
    ],
)
def test_localize_currency(unit: str | None, currency: str, expected: str | None) -> None:
    """The $ placeholder is replaced with the currency and other units pass through."""
    assert localize_currency(unit, currency) == expected


@pytest.mark.parametrize(
    ("currency", "expected"),
    [
        ("AUD", "$"),
        ("USD", "$"),
        ("EUR", "€"),
        ("GBP", "£"),
        ("XYZ", "XYZ"),
    ],
)
def test_currency_symbol(currency: str, expected: str) -> None:
    """Known currency codes map to their symbol and unknown codes are shown as the code."""
    assert currency_symbol(currency) == expected


@pytest.mark.parametrize(
    ("unit", "expected_value", "expected_unit"),
    [
        pytest.param("$/kWh", 0.3, "$/kWh", id="dollars_per_kwh"),
        pytest.param("AUD/kWh", 0.3, "AUD/kWh", id="currency_code_per_kwh"),
        pytest.param("€/MWh", 0.0003, "€/kWh", id="per_mwh"),
        pytest.param("£/Wh", 300.0, "£/kWh", id="per_wh"),
        pytest.param("c/kWh", 0.003, "$/kWh", id="cents_per_kwh"),
        pytest.param("¢/kWh", 0.003, "$/kWh", id="cent_sign_per_kwh"),
        pytest.param("p/MWh", 0.000003, "£/kWh", id="pence_per_mwh"),
        pytest.param("$/kWh/h", 0.3, "$/kWh/h", id="price_rate_unchanged"),
        pytest.param("ct/kWh", 0.003, "€/kWh", id="euro_cents_per_kwh"),
        pytest.param("c / kWh", 0.003, "$/kWh", id="spaced_cents_per_kwh"),
        pytest.param("€ / MWh", 0.0003, "€/kWh", id="spaced_per_mwh"),
    ],
)
def test_prices_convert_to_currency_per_kwh(unit: str, expected_value: float, expected_unit: str) -> None:
    """A price per energy unit converts to the same currency per kWh."""
    value, base_unit, _ = convert_to_base_unit(0.3, unit, None)

    assert value == pytest.approx(expected_value)
    assert base_unit == expected_unit


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        pytest.param("£/kWh", "£", id="symbol"),
        pytest.param("EUR/MWh", "EUR", id="code"),
        pytest.param("A$/kWh", "A$", id="prefixed_symbol"),
        pytest.param("c/kWh", None, id="cents"),
        pytest.param("ct/kWh", "€", id="euro_cents"),
        pytest.param("p/MWh", "£", id="pence"),
        pytest.param("£ / kWh", "£", id="spaced"),
        pytest.param("$/kWh/h", None, id="price_rate"),
        pytest.param("kWh", None, id="energy"),
        pytest.param(None, None, id="no_unit"),
    ],
)
def test_price_currency(unit: str | None, expected: str | None) -> None:
    """A price names its currency, pence and euro cents name their main currency, and plain cents name none."""
    assert price_currency(unit) == expected


def test_convert_to_base_unit_rejects_zero_in_a_reciprocal_unit() -> None:
    """Zero km/kWh has no finite value in kWh/km."""
    with pytest.raises(ValueError, match="reciprocal"):
        convert_to_base_unit(0.0, "km/kWh", None)


def test_unit_conversion_applies_to_a_series() -> None:
    """A series of values sharing a unit converts element by element."""
    np.testing.assert_allclose(UnitConversion(0.5).apply(np.array([2.0, 4.0])), [1.0, 2.0])
    np.testing.assert_allclose(UnitConversion(1.0, reciprocal=True).apply(np.array([4.0, 5.0])), [0.25, 0.2])
