"""Core unit conversion helpers with no Home Assistant dependencies."""

from collections.abc import Mapping
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
    DURATION = "duration"

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
    DOLLAR_PER_KWH_PER_HOUR = "$/kWh/h"
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
    SECOND = "s"
    MINUTE = "min"
    HOUR = "h"
    DAY = "d"

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
    DeviceClass.DURATION: UnitOfMeasurement.HOUR,
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

_TIME_TO_HOURS: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.SECOND: 1.0 / 3600.0,
    UnitOfMeasurement.MINUTE: 1.0 / 60.0,
    UnitOfMeasurement.HOUR: 1.0,
    UnitOfMeasurement.DAY: 24.0,
}

DURATION_UNITS: Final[tuple[UnitOfMeasurement, ...]] = tuple(_TIME_TO_HOURS)

ENERGY_DISTANCE_UNITS: Final[tuple[UnitOfMeasurement, ...]] = tuple(_ENERGY_DISTANCE_TO_KWH_PER_KM)

ENERGY_UNITS: Final[tuple[UnitOfMeasurement, ...]] = (
    UnitOfMeasurement.WATT_HOUR,
    UnitOfMeasurement.KILO_WATT_HOUR,
    UnitOfMeasurement.MEGA_WATT_HOUR,
    UnitOfMeasurement.GIGA_WATT_HOUR,
)

# Matches any currency followed by / and an energy unit (e.g. "£/kWh", "€/MWh")
PRICE_UNIT_SPEC: Final[list[UnitSpec]] = [("*", "/", u.value) for u in ENERGY_UNITS]


# Display symbols for common ISO 4217 currency codes. Codes not listed are shown
# as the code itself, which is unambiguous.
CURRENCY_SYMBOLS: Final[Mapping[str, str]] = {
    "AUD": "$",
    "BRL": "R$",
    "CAD": "$",
    "CHF": "CHF",
    "CNY": "¥",
    "CZK": "Kč",
    "DKK": "kr",
    "EUR": "€",
    "GBP": "£",
    "HKD": "$",
    "HUF": "Ft",
    "ILS": "₪",
    "INR": "₹",
    "JPY": "¥",
    "KRW": "₩",
    "MXN": "$",
    "NOK": "kr",
    "NZD": "$",
    "PLN": "zł",
    "RON": "lei",
    "SEK": "kr",
    "SGD": "$",
    "THB": "฿",
    "TRY": "₺",
    "TWD": "$",
    "UAH": "₴",
    "USD": "$",
    "ZAR": "R",
}


def currency_symbol(currency: str) -> str:
    """Return the display symbol for an ISO 4217 currency code."""
    return CURRENCY_SYMBOLS.get(currency, currency)


def localize_currency(unit: str | None, currency: str) -> str | None:
    """Replace the ``$`` placeholder in a unit string with a currency symbol.

    Monetary units carry ``$`` as a placeholder (e.g. ``$/kWh``, ``$/kWh/h``, ``$``)
    until a Home Assistant display boundary substitutes the user's currency.
    """
    if unit is None:
        return None
    return unit.replace("$", currency)


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

    if unit in _TIME_TO_HOURS:
        return DeviceClass.DURATION

    return None


def base_unit_for_device_class(device_class: DeviceClass | None) -> UnitOfMeasurement | None:
    """Get the canonical base unit for a given device class."""
    return BASE_UNITS.get(device_class) if device_class is not None else None


_TO_BASE_FACTORS: Final[dict[DeviceClass, dict[UnitOfMeasurement, float]]] = {
    DeviceClass.POWER: _POWER_TO_KW,
    DeviceClass.ENERGY: _ENERGY_TO_KWH,
    DeviceClass.ENERGY_STORAGE: _ENERGY_TO_KWH,
    DeviceClass.DISTANCE: _LENGTH_TO_KM,
    DeviceClass.ENERGY_DISTANCE: _ENERGY_DISTANCE_TO_KWH_PER_KM,
    DeviceClass.DURATION: _TIME_TO_HOURS,
}


def _base_factor(unit: UnitOfMeasurement | None, device_class: DeviceClass | None) -> float | None:
    """Return the factor converting *unit* to the device class's base unit, or None if it cannot."""
    base_unit = base_unit_for_device_class(device_class)
    if unit is None or base_unit is None or device_class is None:
        return None
    if unit == base_unit:
        return 1.0
    return _TO_BASE_FACTORS[device_class].get(unit)


def base_unit_conversion(
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[float, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Return the scale factor to the base unit, the base unit, and the parsed device class.

    Conversion to base units is a pure scaling, so a series of values sharing a
    unit converts by multiplying every value by the one factor. A unit with no
    conversion to the base unit, such as the reciprocal km/kWh for energy per
    distance, keeps its own unit and a factor of 1 so selectors filter it out.
    """
    parsed_unit = UnitOfMeasurement.of(unit)
    parsed_device_class = DeviceClass.of(device_class)
    effective_device_class = parsed_device_class or _infer_device_class_from_unit(parsed_unit)

    if unit is None:
        return 1.0, base_unit_for_device_class(effective_device_class), parsed_device_class

    factor = _base_factor(parsed_unit, effective_device_class)
    if factor is None:
        return 1.0, parsed_unit or unit, parsed_device_class

    return factor, base_unit_for_device_class(effective_device_class), parsed_device_class


def convert_to_base_unit(
    value: float,
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[float, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Convert value to base unit, parsing string unit/device_class if needed."""
    factor, base_unit, parsed_device_class = base_unit_conversion(unit, device_class)
    return value * factor, base_unit, parsed_device_class
