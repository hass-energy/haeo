"""Input field metadata for creating input entities.

Defines which config fields should become input entities (NumberEntity/SwitchEntity)
and their associated metadata like output type, direction, and time series behavior.
"""

from dataclasses import dataclass
from typing import TypeGuard

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription


@dataclass(frozen=True, slots=True)
class NumberInputFieldInfo:
    """Metadata for a config field that becomes a number input entity.

    Attributes:
        field_name: The key in the element's ConfigSchema
        entity_description: Home Assistant number entity description with UI metadata
        output_type: From model.const OUTPUT_TYPE_* for categorization
        direction: "+" or "-" for power direction attributes
        time_series: Whether this field is time series (list) or scalar

    """

    field_name: str
    entity_description: NumberEntityDescription
    output_type: str
    direction: str | None = None
    time_series: bool = False


@dataclass(frozen=True, slots=True)
class SwitchInputFieldInfo:
    """Metadata for a config field that becomes a switch input entity.

    Attributes:
        field_name: The key in the element's ConfigSchema
        entity_description: Home Assistant switch entity description with UI metadata
        output_type: From model.const OUTPUT_TYPE_* for categorization
        direction: "+" or "-" for power direction attributes
        time_series: Whether this field is time series (list) or scalar

    """

    field_name: str
    entity_description: SwitchEntityDescription
    output_type: str
    direction: str | None = None
    time_series: bool = False


# Union type for mixed collections of input fields
type InputFieldInfo = NumberInputFieldInfo | SwitchInputFieldInfo


def is_number_field(field: InputFieldInfo) -> TypeGuard[NumberInputFieldInfo]:
    """Check if an input field is a number field."""
    return isinstance(field, NumberInputFieldInfo)


def is_switch_field(field: InputFieldInfo) -> TypeGuard[SwitchInputFieldInfo]:
    """Check if an input field is a switch field."""
    return isinstance(field, SwitchInputFieldInfo)


__all__ = [
    "InputFieldInfo",
    "NumberInputFieldInfo",
    "SwitchInputFieldInfo",
    "is_number_field",
    "is_switch_field",
]
