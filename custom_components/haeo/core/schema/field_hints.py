"""Declarative hints for input fields.

This module provides an HA-free way to define metadata for input fields
alongside their schema definitions. The elements layer will transform these
hints into full HA InputFieldInfo and EntityDescription objects.
"""

from dataclasses import dataclass
from typing import Annotated, Literal, NotRequired, Required, get_args, get_origin, get_type_hints

from custom_components.haeo.core.model.const import OutputType


@dataclass(frozen=True, slots=True)
class FieldHint:
    """Metadata for a config field that becomes an input entity.

    Attributes:
        output_type: Semantic type of the output (POWER, ENERGY, etc.).
            Drives default HA unit, device_class, min, max, and step values.
        direction: "+" or "-" for power direction attributes.
        time_series: Whether this field is time series (list) or scalar.
        boundaries: Whether time series values are at boundaries (n+1) vs intervals (n).
        min_value: Override default min value for the OutputType.
        max_value: Override default max value for the OutputType.
        step: Override default step value for the OutputType.
        default_mode: Controls config flow pre-selection ('entity' or 'value').
        default_value: Value to pre-fill when default_mode='value'.
        force_required: Force value to be required, overriding schema optionality.
        device_type: Optional device type override for sub-device inputs.

    """

    output_type: OutputType
    direction: str | None = None
    time_series: bool = False
    boundaries: bool = False
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    default_mode: Literal["entity", "value"] | None = None
    default_value: float | bool | None = None
    force_required: bool | None = None
    device_type: str | None = None


@dataclass(frozen=True, slots=True)
class SectionHints:
    """Wrapper for field hints to use in Annotated metadata."""

    fields: dict[str, FieldHint]


def extract_field_hints(schema_cls: type) -> dict[str, dict[str, FieldHint]]:
    """Extract declarative field hints from a TypedDict's Annotated metadata."""
    hints = get_type_hints(schema_cls, include_extras=True)
    result: dict[str, dict[str, FieldHint]] = {}

    for section_key, section_type in hints.items():
        origin = get_origin(section_type)
        if origin in (Required, NotRequired):
            unwrapped_type = get_args(section_type)[0]
            origin = get_origin(unwrapped_type)
        else:
            unwrapped_type = section_type

        if origin is Annotated:
            for arg in get_args(unwrapped_type)[1:]:
                if isinstance(arg, SectionHints):
                    result[section_key] = arg.fields
                    break

    return result
