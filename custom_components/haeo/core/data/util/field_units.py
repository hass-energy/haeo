"""Check and convert source values against the unit an input field expects."""

from typing import Final

from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.util import UnitSpec, matches_unit_spec
from custom_components.haeo.core.units import UnitOfMeasurement, base_unit_conversion

# Physical quantities that cannot be negative. Prices can, and switches have no sign.
NON_NEGATIVE_OUTPUT_TYPES: Final = frozenset(
    {
        OutputType.POWER,
        OutputType.POWER_LIMIT,
        OutputType.ENERGY,
        OutputType.STATE_OF_CHARGE,
        OutputType.EFFICIENCY,
        OutputType.DURATION,
        OutputType.DISTANCE,
        OutputType.ENERGY_PER_DISTANCE,
    }
)

# The base unit each input field's values are in, with how to name it to a user
_FIELD_UNITS: Final[dict[OutputType, tuple[UnitSpec, str]]] = {
    OutputType.POWER: (UnitOfMeasurement.KILO_WATT.value, UnitOfMeasurement.KILO_WATT.value),
    OutputType.POWER_FLOW: (UnitOfMeasurement.KILO_WATT.value, UnitOfMeasurement.KILO_WATT.value),
    OutputType.POWER_LIMIT: (UnitOfMeasurement.KILO_WATT.value, UnitOfMeasurement.KILO_WATT.value),
    OutputType.ENERGY: (UnitOfMeasurement.KILO_WATT_HOUR.value, UnitOfMeasurement.KILO_WATT_HOUR.value),
    OutputType.DURATION: (UnitOfMeasurement.HOUR.value, UnitOfMeasurement.HOUR.value),
    OutputType.STATE_OF_CHARGE: (UnitOfMeasurement.PERCENT.value, UnitOfMeasurement.PERCENT.value),
    OutputType.EFFICIENCY: (UnitOfMeasurement.PERCENT.value, UnitOfMeasurement.PERCENT.value),
    OutputType.PRICE: (("*", "/", UnitOfMeasurement.KILO_WATT_HOUR.value), UnitOfMeasurement.DOLLAR_PER_KWH.value),
    OutputType.DISTANCE: (UnitOfMeasurement.KILOMETER.value, UnitOfMeasurement.KILOMETER.value),
    OutputType.ENERGY_PER_DISTANCE: (
        UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER.value,
        UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOMETER.value,
    ),
}


def has_field_unit(output_type: OutputType) -> bool:
    """Return True when an input field's values carry a unit."""
    return output_type in _FIELD_UNITS


def field_unit_spec(output_type: OutputType) -> UnitSpec | None:
    """Return the unit an input field's values are in, which a source's values must convert to.

    Returns None for a field without a unit.
    """
    return _FIELD_UNITS[output_type][0] if output_type in _FIELD_UNITS else None


def source_units(output_type: OutputType) -> tuple[str, ...]:
    """Return the units a source can state for an input field, those that convert to its unit."""
    spec = _FIELD_UNITS[output_type][0]
    return tuple(
        unit.value for unit in UnitOfMeasurement if matches_unit_spec(str(base_unit_conversion(unit, None)[1]), spec)
    )


def check_source_unit(base_unit: str | None, output_type: OutputType) -> None:
    """Reject a source whose values, converted to base units, are not in the field's unit.

    A source that states no unit, or a field without one, passes.

    Raises:
        InputError: If the source's unit cannot convert to the field's unit.

    """
    if base_unit is None or output_type not in _FIELD_UNITS:
        return
    if not matches_unit_spec(base_unit, _FIELD_UNITS[output_type][0]):
        raise InputError(
            translation_key="input_unit_incompatible",
            translation_placeholders={"unit": base_unit, "expected": ", ".join(source_units(output_type))},
        )


def field_unit_label(output_type: OutputType) -> str | None:
    """Return how to name an input field's unit to a user, or None when it has none."""
    return _FIELD_UNITS[output_type][1] if output_type in _FIELD_UNITS else None


def to_field_unit(value: float, unit: str | None, output_type: OutputType) -> float | None:
    """Convert a value typed with a unit, such as in a calendar event, to the field's unit.

    A field with a unit needs the value to state a convertible unit; a bare
    number is never taken to be in HAEO's own units. A field without a unit
    takes a bare number. A quantity that cannot be negative takes no negative
    value, and a reciprocal unit, such as km/kWh, takes no zero. Returns None
    for a value the field cannot use.
    """
    if value < 0 and output_type in NON_NEGATIVE_OUTPUT_TYPES:
        return None
    if output_type not in _FIELD_UNITS:
        return value if unit is None else None
    if unit is None:
        return None
    conversion, base_unit, _ = base_unit_conversion(unit, None)
    if not matches_unit_spec(str(base_unit), _FIELD_UNITS[output_type][0]):
        return None
    try:
        return conversion.apply(value)
    except ValueError:
        return None


__all__ = [
    "NON_NEGATIVE_OUTPUT_TYPES",
    "check_source_unit",
    "field_unit_label",
    "field_unit_spec",
    "has_field_unit",
    "source_units",
    "to_field_unit",
]
