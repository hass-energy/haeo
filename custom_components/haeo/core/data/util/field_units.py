"""Check and convert source values against the unit an input field expects."""

from typing import Final

from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.util import UnitSpec, matches_unit_spec
from custom_components.haeo.core.units import UnitOfMeasurement, base_unit_conversion

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
}


def has_field_unit(output_type: OutputType) -> bool:
    """Return True when an input field's values carry a unit."""
    return output_type in _FIELD_UNITS


def check_source_unit(base_unit: str | None, output_type: OutputType) -> None:
    """Reject a source whose values, converted to base units, are not in the field's unit.

    A source that states no unit, or a field without one, passes.

    Raises:
        InputError: If the source's unit cannot convert to the field's unit.

    """
    if base_unit is None or output_type not in _FIELD_UNITS:
        return
    spec, expected = _FIELD_UNITS[output_type]
    if not matches_unit_spec(base_unit, spec):
        raise InputError(
            translation_key="input_unit_incompatible",
            translation_placeholders={"unit": base_unit, "expected": expected},
        )


def to_field_unit(value: float, unit: str | None, output_type: OutputType) -> float:
    """Convert a value typed with a unit, such as in a calendar event, to the field's unit.

    A field with a unit needs the value to state a convertible unit; a bare
    number is never taken to be in HAEO's own units. A field without a unit
    takes a bare number.

    Raises:
        InputError: If the value has no unit where the field needs one, has a
            unit where the field has none, or has a unit that does not convert.

    """
    if output_type not in _FIELD_UNITS:
        if unit is not None:
            raise InputError(
                translation_key="input_unit_unexpected",
                translation_placeholders={"value": f"{value:g} {unit}"},
            )
        return value
    if unit is None:
        raise InputError(
            translation_key="input_unit_missing",
            translation_placeholders={"value": f"{value:g}", "expected": _FIELD_UNITS[output_type][1]},
        )
    factor, base_unit, _ = base_unit_conversion(unit, None)
    check_source_unit(str(base_unit), output_type)
    return value * factor


__all__ = ["check_source_unit", "has_field_unit", "to_field_unit"]
