"""Tests for base unit conversion utilities."""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfPower
import pytest

from custom_components.haeo.data.loader.extractors.utils.base_unit import (
    base_unit_for_device_class,
    convert_to_base_unit,
)


@pytest.mark.parametrize(
    ("device_class", "expected"),
    [
        (SensorDeviceClass.POWER, "kW"),
        (SensorDeviceClass.ENERGY, "kWh"),
        (SensorDeviceClass.ENERGY_STORAGE, "kWh"),
        (SensorDeviceClass.TEMPERATURE, None),
        (SensorDeviceClass.HUMIDITY, None),
        (SensorDeviceClass.PRESSURE, None),
        (None, None),
    ],
)
def test_base_unit_for_device_class(device_class: SensorDeviceClass | None, expected: str | None) -> None:
    """Test base unit lookup for various device classes."""
    assert base_unit_for_device_class(device_class) == expected


@pytest.mark.parametrize(
    ("value", "unit", "device_class", "expected"),
    [
        # Power conversions
        (1000.0, "W", SensorDeviceClass.POWER, 1.0),
        (1.0, "MW", SensorDeviceClass.POWER, 1000.0),
        (1.0, UnitOfPower.WATT, SensorDeviceClass.POWER, 0.001),
        (1.0, UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, 1.0),
        # Energy conversions
        (1000.0, "Wh", SensorDeviceClass.ENERGY, 1.0),
        (1.0, "MWh", SensorDeviceClass.ENERGY, 1000.0),
        (5.0, "kWh", SensorDeviceClass.ENERGY, 5.0),
        # Energy storage uses same base unit as energy
        (1000.0, "Wh", SensorDeviceClass.ENERGY_STORAGE, 1.0),
        # No conversion when already in base unit
        (5.0, "kW", SensorDeviceClass.POWER, 5.0),
        # No conversion for None device class
        (100.0, "W", None, 100.0),
        # No conversion for unsupported device classes (have HA converters but no base unit)
        (25.0, "°C", SensorDeviceClass.TEMPERATURE, 25.0),
        (50.0, "%", SensorDeviceClass.HUMIDITY, 50.0),
        (75.0, "%", SensorDeviceClass.BATTERY, 75.0),
        # No conversion for device classes without HA converters
        (100.0, "$", SensorDeviceClass.MONETARY, 100.0),
        # No conversion when from_unit is None
        (100.0, None, SensorDeviceClass.POWER, 100.0),
    ],
)
def test_convert_to_base_unit(
    value: float,
    unit: str | None,
    device_class: SensorDeviceClass | None,
    expected: float,
) -> None:
    """Test unit conversion to base units for various device classes and units."""
    assert convert_to_base_unit(value, unit, device_class) == pytest.approx(expected)
