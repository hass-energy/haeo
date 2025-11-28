"""Utilities for converting sensor values to base units."""

from typing import Final

from homeassistant.components.sensor.const import UNIT_CONVERTERS, SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower

BASE_UNITS: Final = {
    SensorDeviceClass.POWER: UnitOfPower.KILO_WATT,
    SensorDeviceClass.ENERGY: UnitOfEnergy.KILO_WATT_HOUR,
    SensorDeviceClass.ENERGY_STORAGE: UnitOfEnergy.KILO_WATT_HOUR,
}


def base_unit_for_device_class(device_class: SensorDeviceClass | None) -> str | None:
    """Get the canonical base unit for a given device class."""
    return BASE_UNITS.get(device_class) if device_class is not None else None


def convert_to_base_unit(value: float, from_unit: str | None, device_class: SensorDeviceClass | None) -> float:
    """Convert *value* expressed in *from_unit* to the canonical base unit."""
    base_unit = base_unit_for_device_class(device_class)
    # Only convert if we have valid from_unit, base_unit, and they differ
    if (
        from_unit is not None
        and base_unit is not None
        and base_unit != from_unit
        and (converter := UNIT_CONVERTERS.get(device_class))
    ):
        return converter.convert(value, from_unit, base_unit)

    return value
