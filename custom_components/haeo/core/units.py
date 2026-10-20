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
_MINOR_CURRENCIES: Final[dict[str, str]] = {"c": "$", "¢": "$", "p": "£"}

_DURATION_TO_HOURS: Final[dict[UnitOfMeasurement, float]] = {
    UnitOfMeasurement.SECOND: 1 / 3600,
    UnitOfMeasurement.MINUTE: 1 / 60,
    UnitOfMeasurement.HOUR: 1.0,
    UnitOfMeasurement.DAY: 24.0,
}

# Factors to each device class's base unit, for every device class that has one
_TO_BASE_UNIT: Final[dict[DeviceClass, dict[UnitOfMeasurement, float]]] = {
    DeviceClass.POWER: _POWER_TO_KW,
    DeviceClass.ENERGY: _ENERGY_TO_KWH,
    DeviceClass.ENERGY_STORAGE: _ENERGY_TO_KWH,
    DeviceClass.DURATION: _DURATION_TO_HOURS,
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

    return None


def base_unit_for_device_class(device_class: DeviceClass | None) -> UnitOfMeasurement | None:
    """Get the canonical base unit for a given device class."""
    return BASE_UNITS.get(device_class) if device_class is not None else None


def _scale_factor(
    from_unit: UnitOfMeasurement | None,
    device_class: DeviceClass | None,
) -> float:
    """Return the factor that converts a value in *from_unit* to the canonical base unit."""
    if from_unit is None:
        return 1.0

    effective_device_class = device_class or _infer_device_class_from_unit(from_unit)
    if effective_device_class is None:
        return 1.0
    return _TO_BASE_UNIT.get(effective_device_class, {}).get(from_unit, 1.0)


def _price_conversion(unit: str | UnitOfMeasurement | None) -> tuple[float, str] | None:
    """Return the factor and base unit for a price per energy unit, such as ``€/MWh`` to ``€/kWh``.

    A price in cents or pence, such as ``c/kWh``, converts to the main unit.
    """
    if not isinstance(unit, str):
        return None
    currency, separator, energy = str(unit).rpartition("/")
    energy_unit = UnitOfMeasurement.of(energy)
    if not separator or not currency or energy_unit is None or energy_unit not in _ENERGY_TO_KWH:
        return None
    main_currency = _MINOR_CURRENCIES.get(currency)
    factor = 1.0 / _ENERGY_TO_KWH[energy_unit] * (0.01 if main_currency else 1.0)
    return factor, f"{main_currency or currency}/{UnitOfMeasurement.KILO_WATT_HOUR}"


def base_unit_conversion(
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[float, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Return the scale factor to the base unit, the base unit, and the parsed device class.

    Conversion to base units is a pure scaling, so a series of values sharing a
    unit converts by multiplying every value by the one factor. A price per
    energy unit converts to the same currency per kWh.
    """
    parsed_unit = UnitOfMeasurement.of(unit)
    parsed_device_class = DeviceClass.of(device_class)
    if parsed_unit is None and (price := _price_conversion(unit)) is not None:
        return price[0], price[1], parsed_device_class
    effective_device_class = parsed_device_class or _infer_device_class_from_unit(parsed_unit)

    factor = _scale_factor(parsed_unit, parsed_device_class)
    base_unit = base_unit_for_device_class(effective_device_class) or parsed_unit or unit

    return factor, base_unit, parsed_device_class


def convert_to_base_unit(
    value: float,
    unit: str | UnitOfMeasurement | None,
    device_class: str | DeviceClass | None,
) -> tuple[float, UnitOfMeasurement | str | None, DeviceClass | None]:
    """Convert value to base unit, parsing string unit/device_class if needed."""
    factor, base_unit, parsed_device_class = base_unit_conversion(unit, device_class)
    return value * factor, base_unit, parsed_device_class
