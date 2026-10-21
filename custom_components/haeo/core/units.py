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
    DURATION = "duration"
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
    DOLLAR_PER_KWH_PER_HOUR = "$/kWh/h"
    PERCENT = "%"
    SECOND = "s"
    MINUTE = "min"
    HOUR = "h"
    DAY = "d"
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
    DeviceClass.DURATION: UnitOfMeasurement.HOUR,
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

# Currency symbols worth a hundredth of a main unit, with the main unit's symbol
_MINOR_CURRENCIES: Final[dict[str, str]] = {"c": "$", "¢": "$", "ct": "€", "p": "£"}

_DURATION_TO_HOURS: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.SECOND: 1 / 3600,
    UnitOfMeasurement.MINUTE: 1 / 60,
    UnitOfMeasurement.HOUR: 1.0,
    UnitOfMeasurement.DAY: 24.0,
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

# Factors to each device class's base unit, for every device class that has one
_TO_BASE_UNIT: Final[dict[DeviceClass, dict[UnitOfMeasurement, float]]] = {
    DeviceClass.POWER: _POWER_TO_KW,
    DeviceClass.ENERGY: _ENERGY_TO_KWH,
    DeviceClass.ENERGY_STORAGE: _ENERGY_TO_KWH,
    DeviceClass.DURATION: _DURATION_TO_HOURS,
    DeviceClass.DISTANCE: _LENGTH_TO_KM,
    DeviceClass.ENERGY_DISTANCE: _ENERGY_DISTANCE_TO_KWH_PER_KM,
}

# Durations HAEO reads from sensors, in units it converts to hours
DURATION_UNITS: Final[tuple[UnitOfMeasurement, ...]] = tuple(_DURATION_TO_HOURS)

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

    if unit in _DURATION_TO_HOURS:
        return DeviceClass.DURATION

    if unit in _LENGTH_TO_KM:
        return DeviceClass.DISTANCE

    if unit in _ENERGY_DISTANCE_TO_KWH_PER_KM:
        return DeviceClass.ENERGY_DISTANCE

    return None


def base_unit_for_device_class(device_class: DeviceClass | None) -> UnitOfMeasurement | None:
    """Get the canonical base unit for a given device class."""
    return BASE_UNITS.get(device_class) if device_class is not None else None


def _base_factor(unit: UnitOfMeasurement | None, device_class: DeviceClass | None) -> float | None:
    """Return the factor converting *unit* to the device class's base unit, or None if it cannot."""
    base_unit = base_unit_for_device_class(device_class)
    if unit is None or base_unit is None or device_class is None:
        return None
    if unit == base_unit:
        return 1.0
    return _TO_BASE_UNIT[device_class].get(unit)


def _price_parts(unit: object) -> tuple[str, float] | None:
    """Return the currency of a price per energy unit and the factor to that currency per kWh.

    A price in cents or pence, such as ``c/kWh``, is stated in the main unit.
    """
    if not isinstance(unit, str):
        return None
    currency, separator, energy = unit.rpartition("/")
    energy_unit = UnitOfMeasurement.of(energy)
    if not separator or not currency or energy_unit is None or energy_unit not in _ENERGY_TO_KWH:
        return None
    factor = 1.0 / _ENERGY_TO_KWH[energy_unit]
    if (main_currency := _MINOR_CURRENCIES.get(currency)) is not None:
        return main_currency, factor * 0.01
    return currency, factor


def price_currency(unit: object) -> str | None:
    """Return the currency a price per energy unit is stated in, or None for any other unit."""
    parts = _price_parts(unit)
    return parts[0] if parts is not None else None


def _price_conversion(unit: object) -> tuple[float, str] | None:
    """Return the factor and base unit for a price per energy unit, such as ``€/MWh`` to ``€/kWh``."""
    parts = _price_parts(unit)
    if parts is None:
        return None
    currency, factor = parts
    return factor, f"{currency}/{UnitOfMeasurement.KILO_WATT_HOUR}"


def base_unit_conversion(
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[float, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Return the scale factor to the base unit, the base unit, and the parsed device class.

    Conversion to base units is a pure scaling, so a series of values sharing a
    unit converts by multiplying every value by the one factor. A price per
    energy unit converts to the same currency per kWh. A unit with no
    conversion to the base unit, such as the reciprocal km/kWh for energy per
    distance, keeps its own unit and a factor of 1, so it never matches the
    unit an input expects.
    """
    parsed_unit = UnitOfMeasurement.of(unit)
    parsed_device_class = DeviceClass.of(device_class)
    if parsed_unit is None and (price := _price_conversion(unit)) is not None:
        return price[0], price[1], parsed_device_class
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
