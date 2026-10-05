"""Core unit conversion helpers with no Home Assistant dependencies."""

from enum import StrEnum
from typing import Final

from custom_components.haeo.core.schema.util import UnitSpec


class DeviceClass(StrEnum):
    """Supported device classes used by core unit conversion."""

    POWER = "power"
    ENERGY = "energy"
    ENERGY_STORAGE = "energy_storage"
    MONETARY = "monetary"
    DISTANCE = "distance"
    ENERGY_DISTANCE = "energy_distance"

    @classmethod
    def of(cls, value: object) -> "DeviceClass | None":
        """Parse an untyped value into a known device class."""
        try:
            return cls(value)
        except (TypeError, ValueError):
            return None


class UnitOfMeasurement(StrEnum):
    """Supported units used by the core pipeline."""

    WATT = "W"
    KILO_WATT = "kW"
    MEGA_WATT = "MW"
    GIGA_WATT = "GW"
    WATT_HOUR = "Wh"
    KILO_WATT_HOUR = "kWh"
    MEGA_WATT_HOUR = "MWh"
    GIGA_WATT_HOUR = "GWh"
    DOLLAR_PER_KWH = "$/kWh"
    PERCENT = "%"
    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    KILOMETER = "km"
    INCH = "in"
    FOOT = "ft"
    YARD = "yd"
    MILE = "mi"
    NAUTICAL_MILE = "nmi"
    WATT_HOUR_PER_KILOMETER = "Wh/km"
    KILO_WATT_HOUR_PER_KILOMETER = "kWh/km"
    KILO_WATT_HOUR_PER_100_KILOMETER = "kWh/100km"

    @classmethod
    def of(cls, value: object) -> "UnitOfMeasurement | None":
        """Parse an untyped value into a known unit of measurement."""
        try:
            return cls(value)
        except (TypeError, ValueError):
            return None


BASE_UNITS: Final[dict[DeviceClass, UnitOfMeasurement]] = {
    DeviceClass.POWER: UnitOfMeasurement.KILO_WATT,
    DeviceClass.ENERGY: UnitOfMeasurement.KILO_WATT_HOUR,
    DeviceClass.ENERGY_STORAGE: UnitOfMeasurement.KILO_WATT_HOUR,
    DeviceClass.DISTANCE: UnitOfMeasurement.KILOMETER,
    DeviceClass.ENERGY_DISTANCE: UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER,
}

_POWER_TO_KW: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.WATT: 0.001,
    UnitOfMeasurement.KILO_WATT: 1.0,
    UnitOfMeasurement.MEGA_WATT: 1000.0,
    UnitOfMeasurement.GIGA_WATT: 1_000_000.0,
}

_ENERGY_TO_KWH: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.WATT_HOUR: 0.001,
    UnitOfMeasurement.KILO_WATT_HOUR: 1.0,
    UnitOfMeasurement.MEGA_WATT_HOUR: 1000.0,
    UnitOfMeasurement.GIGA_WATT_HOUR: 1_000_000.0,
}

_LENGTH_TO_KM: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.MILLIMETER: 0.000001,
    UnitOfMeasurement.CENTIMETER: 0.00001,
    UnitOfMeasurement.METER: 0.001,
    UnitOfMeasurement.KILOMETER: 1.0,
    UnitOfMeasurement.INCH: 0.0000254,
    UnitOfMeasurement.FOOT: 0.0003048,
    UnitOfMeasurement.YARD: 0.0009144,
    UnitOfMeasurement.MILE: 1.609344,
    UnitOfMeasurement.NAUTICAL_MILE: 1.852,
}

# Consumption units only: distance-per-energy units (km/kWh, mi/kWh) are
# reciprocal and have no finite conversion for a zero reading.
_ENERGY_DISTANCE_TO_KWH_PER_KM: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.WATT_HOUR_PER_KILOMETER: 0.001,
    UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER: 1.0,
    UnitOfMeasurement.KILO_WATT_HOUR_PER_100_KILOMETER: 0.01,
}

ENERGY_DISTANCE_UNITS: Final[tuple[UnitOfMeasurement, ...]] = tuple(_ENERGY_DISTANCE_TO_KWH_PER_KM)

ENERGY_UNITS: Final[tuple[UnitOfMeasurement, ...]] = (
    UnitOfMeasurement.WATT_HOUR,
    UnitOfMeasurement.KILO_WATT_HOUR,
    UnitOfMeasurement.MEGA_WATT_HOUR,
    UnitOfMeasurement.GIGA_WATT_HOUR,
)

# Matches any currency followed by / and an energy unit (e.g. "£/kWh", "€/MWh")
PRICE_UNIT_SPEC: Final[list[UnitSpec]] = [("*", "/", u.value) for u in ENERGY_UNITS]


def _infer_device_class_from_unit(unit: UnitOfMeasurement | None) -> DeviceClass | None:
    """Infer a device class from unit when no explicit class is available."""
    if unit in {
        UnitOfMeasurement.WATT,
        UnitOfMeasurement.KILO_WATT,
        UnitOfMeasurement.MEGA_WATT,
        UnitOfMeasurement.GIGA_WATT,
    }:
        return DeviceClass.POWER

    if unit in {
        UnitOfMeasurement.WATT_HOUR,
        UnitOfMeasurement.KILO_WATT_HOUR,
        UnitOfMeasurement.MEGA_WATT_HOUR,
        UnitOfMeasurement.GIGA_WATT_HOUR,
    }:
        return DeviceClass.ENERGY

    if unit in _LENGTH_TO_KM:
        return DeviceClass.DISTANCE

    if unit in _ENERGY_DISTANCE_TO_KWH_PER_KM:
        return DeviceClass.ENERGY_DISTANCE

    return None


def base_unit_for_device_class(device_class: DeviceClass | None) -> UnitOfMeasurement | None:
    """Get the canonical base unit for a given device class."""
    return BASE_UNITS.get(device_class) if device_class is not None else None


def _convert_value(
    value: float,
    from_unit: UnitOfMeasurement | None,
    device_class: DeviceClass | None,
) -> float:
    """Convert *value* expressed in *from_unit* to the canonical base unit."""
    if from_unit is None:
        return value

    effective_device_class = device_class or _infer_device_class_from_unit(from_unit)
    base_unit = base_unit_for_device_class(effective_device_class)
    if base_unit is None or base_unit == from_unit:
        return value

    if effective_device_class == DeviceClass.POWER:
        factor = _POWER_TO_KW.get(from_unit)
        return value * factor if factor is not None else value

    if effective_device_class in {DeviceClass.ENERGY, DeviceClass.ENERGY_STORAGE}:
        factor = _ENERGY_TO_KWH.get(from_unit)
        return value * factor if factor is not None else value

    if effective_device_class == DeviceClass.DISTANCE:
        factor = _LENGTH_TO_KM.get(from_unit)
        return value * factor if factor is not None else value

    if effective_device_class == DeviceClass.ENERGY_DISTANCE:
        factor = _ENERGY_DISTANCE_TO_KWH_PER_KM.get(from_unit)
        return value * factor if factor is not None else value

    return value


def convert_to_base_unit(
    value: float,
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[float, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Convert value to base unit, parsing string unit/device_class if needed."""
    parsed_unit = UnitOfMeasurement.of(unit)
    parsed_device_class = DeviceClass.of(device_class)
    effective_device_class = parsed_device_class or _infer_device_class_from_unit(parsed_unit)

    converted_value = _convert_value(value, parsed_unit, parsed_device_class)
    base_unit = base_unit_for_device_class(effective_device_class) or parsed_unit or unit

    return converted_value, base_unit, parsed_device_class
