"""Tests for base unit conversion utilities."""

import pytest

from custom_components.haeo.core.units import (
    DeviceClass,
    UnitOfMeasurement,
    base_unit_for_device_class,
    convert_to_base_unit,
    normalize_measurement,
)


@pytest.mark.parametrize(
    ("device_class", "expected"),
    [
        (DeviceClass.POWER, "kW"),
        (DeviceClass.ENERGY, "kWh"),
        (DeviceClass.ENERGY_STORAGE, "kWh"),
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
def test_convert_to_base_unit(
    value: float,
    unit: UnitOfMeasurement | None,
    device_class: DeviceClass | None,
    expected: float,
) -> None:
    """Test unit conversion to base units for various device classes and units."""
    assert convert_to_base_unit(value, unit, device_class) == pytest.approx(expected)


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
            12.0,
            "unknown_unit",
            None,
            (12.0, "unknown_unit", None),
        ),
    ],
)
def test_normalize_measurement(
    value: float,
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
    expected: tuple[float, UnitOfMeasurement | str | None, DeviceClass | None],
) -> None:
    """Normalize value and metadata consistently in one call."""
    normalized_value, normalized_unit, normalized_device_class = normalize_measurement(value, unit, device_class)
    expected_value, expected_unit, expected_device_class = expected
    assert normalized_value == pytest.approx(expected_value)
    assert normalized_unit == expected_unit
    assert normalized_device_class == expected_device_class
