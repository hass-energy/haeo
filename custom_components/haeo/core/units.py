"""Core unit conversion helpers with no Home Assistant dependencies."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, overload

import numpy as np
from numpy.typing import NDArray


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
    KILOMETER_PER_KILO_WATT_HOUR = "km/kWh"
    MILE_PER_KILO_WATT_HOUR = "mi/kWh"

    @classmethod
    def of(cls, value: object) -> "UnitOfMeasurement | None":
        """Parse an untyped value into a known unit of measurement, ignoring whitespace.

        Integrations write some units with spaces, such as ``kWh/100 km``.
        """
        try:
            return cls(_compact(value) if isinstance(value, str) else value)
        except (TypeError, ValueError):
            return None


def _compact(unit: str) -> str:
    """Remove the whitespace from a unit, which no unit HAEO reads contains."""
    return "".join(unit.split())


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

# Currency symbols worth a hundredth of a main unit, with the main unit's symbol.
# Cents written as c or ¢ are used by many currencies, so they name none.
_MINOR_CURRENCIES: Final[dict[str, str | None]] = {"c": None, "¢": None, "ct": "€", "p": "£"}

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

_ENERGY_DISTANCE_TO_KWH_PER_KM: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.WATT_HOUR_PER_KILOMETER: 0.001,
    UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER: 1.0,
    UnitOfMeasurement.KILO_WATT_HOUR_PER_100_KILOMETER: 0.01,
}

# Distance per energy, the reciprocal of energy per distance, to km/kWh
_DISTANCE_ENERGY_TO_KM_PER_KWH: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.KILOMETER_PER_KILO_WATT_HOUR: 1.0,
    UnitOfMeasurement.MILE_PER_KILO_WATT_HOUR: 1.609344,
}

# Factors to each device class's base unit, for every device class that has one
_TO_BASE_UNIT: Final[dict[DeviceClass, dict[UnitOfMeasurement, float]]] = {
    DeviceClass.POWER: _POWER_TO_KW,
    DeviceClass.ENERGY: _ENERGY_TO_KWH,
    DeviceClass.ENERGY_STORAGE: _ENERGY_TO_KWH,
    DeviceClass.DURATION: _DURATION_TO_HOURS,
    DeviceClass.DISTANCE: _LENGTH_TO_KM,
    DeviceClass.ENERGY_DISTANCE: _ENERGY_DISTANCE_TO_KWH_PER_KM,
}

# Factors to the reciprocal of each device class's base unit, for units stated that way
_TO_RECIPROCAL_BASE_UNIT: Final[dict[DeviceClass, dict[UnitOfMeasurement, float]]] = {
    DeviceClass.ENERGY_DISTANCE: _DISTANCE_ENERGY_TO_KM_PER_KWH,
}


@dataclass(frozen=True, slots=True)
class UnitConversion:
    """How values in a unit convert to their base unit.

    Values are scaled by ``factor``, then inverted when the unit is the
    reciprocal of the base unit, as km/kWh is of kWh/km.
    """

    factor: float = 1.0
    reciprocal: bool = False

    @overload
    def apply(self, values: float) -> float: ...
    @overload
    def apply(self, values: NDArray[np.float64]) -> NDArray[np.float64]: ...
    def apply(self, values: float | NDArray[np.float64]) -> float | NDArray[np.float64]:
        """Convert values to the base unit.

        Raises:
            ValueError: If a value in a reciprocal unit is zero, which has no
                finite value in the base unit.

        """
        scaled = values * self.factor
        if not self.reciprocal:
            return scaled
        if np.any(np.equal(scaled, 0)):
            msg = "A zero in a reciprocal unit has no finite value in the base unit"
            raise ValueError(msg)
        return 1 / scaled


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

    if unit in _ENERGY_DISTANCE_TO_KWH_PER_KM or unit in _DISTANCE_ENERGY_TO_KM_PER_KWH:
        return DeviceClass.ENERGY_DISTANCE

    return None


def base_unit_for_device_class(device_class: DeviceClass | None) -> UnitOfMeasurement | None:
    """Get the canonical base unit for a given device class."""
    return BASE_UNITS.get(device_class) if device_class is not None else None


def _base_conversion(unit: UnitOfMeasurement | None, device_class: DeviceClass | None) -> UnitConversion | None:
    """Return how *unit* converts to the device class's base unit, or None if it cannot."""
    base_unit = base_unit_for_device_class(device_class)
    if unit is None or base_unit is None or device_class is None:
        return None
    if unit == base_unit:
        return UnitConversion()
    if (factor := _TO_BASE_UNIT[device_class].get(unit)) is not None:
        return UnitConversion(factor)
    if (factor := _TO_RECIPROCAL_BASE_UNIT.get(device_class, {}).get(unit)) is not None:
        return UnitConversion(factor, reciprocal=True)
    return None


def _price_parts(unit: object) -> tuple[str | None, float] | None:
    """Return the currency of a price per energy unit and the factor to that currency per kWh.

    A price in cents or pence, such as ``c/kWh``, is stated in the main unit.
    Cents written as ``c`` or ``¢`` name no currency, so the currency is None.
    Returns None for a unit that is not a price per energy unit.
    """
    if not isinstance(unit, str):
        return None
    currency, separator, energy = _compact(unit).rpartition("/")
    energy_unit = UnitOfMeasurement.of(energy)
    if not separator or not currency or energy_unit is None or energy_unit not in _ENERGY_TO_KWH:
        return None
    factor = 1.0 / _ENERGY_TO_KWH[energy_unit]
    if currency in _MINOR_CURRENCIES:
        return _MINOR_CURRENCIES[currency], factor * 0.01
    return currency, factor


def price_currency(unit: object) -> str | None:
    """Return the currency a price per energy unit is stated in.

    Returns None for any other unit, and for cents written as ``c`` or ``¢``,
    which belong to whichever currency the other prices are in.
    """
    parts = _price_parts(unit)
    return parts[0] if parts is not None else None


def _price_conversion(unit: object) -> tuple[UnitConversion, str] | None:
    """Return the conversion and base unit for a price per energy unit, such as ``€/MWh`` to ``€/kWh``.

    Cents that name no currency convert to HAEO's ``$`` currency placeholder.
    """
    parts = _price_parts(unit)
    if parts is None:
        return None
    currency, factor = parts
    if currency is None:
        return UnitConversion(factor), UnitOfMeasurement.DOLLAR_PER_KWH.value
    return UnitConversion(factor), f"{currency}/{UnitOfMeasurement.KILO_WATT_HOUR}"


def base_unit_conversion(
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[UnitConversion, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Return the conversion to the base unit, the base unit, and the parsed device class.

    A series of values sharing a unit converts with the one conversion. A price
    per energy unit converts to the same currency per kWh. A unit with no
    conversion to the base unit keeps its own unit and converts unchanged, so
    it never matches the unit an input expects.
    """
    parsed_unit = UnitOfMeasurement.of(unit)
    parsed_device_class = DeviceClass.of(device_class)
    if parsed_unit is None and (price := _price_conversion(unit)) is not None:
        return price[0], price[1], parsed_device_class
    effective_device_class = parsed_device_class or _infer_device_class_from_unit(parsed_unit)

    if unit is None:
        return UnitConversion(), base_unit_for_device_class(effective_device_class), parsed_device_class

    conversion = _base_conversion(parsed_unit, effective_device_class)
    if conversion is None:
        return UnitConversion(), parsed_unit or unit, parsed_device_class

    return conversion, base_unit_for_device_class(effective_device_class), parsed_device_class


def convert_to_base_unit(
    value: float,
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[float, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Convert value to base unit, parsing string unit/device_class if needed.

    Raises:
        ValueError: If the value is zero in a reciprocal unit.

    """
    conversion, base_unit, parsed_device_class = base_unit_conversion(unit, device_class)
    return conversion.apply(value), base_unit, parsed_device_class
