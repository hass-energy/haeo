"""Input field metadata for creating input entities.

Defines which config fields should become input entities (NumberEntity/SwitchEntity)
and their associated metadata like output type, direction, and time series behavior.
"""

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription

from custom_components.haeo.model.const import OutputType


@dataclass(frozen=True, slots=True)
class InputFieldInfo[T: (NumberEntityDescription, SwitchEntityDescription)]:
    """Metadata for a config field that becomes an input entity.

    Attributes:
        entity_description: Home Assistant entity description (Number or Switch)
        output_type: OutputType enum value for categorization and unit spec lookup
        direction: "+" or "-" for power direction attributes
        time_series: Whether this field is time series (list) or scalar
        default: Default value for editable entities when no restored state exists

    Note:
        Whether a field is optional (can be disabled in config flow) is determined
        by the element's ConfigSchema TypedDict using NotRequired. Use the TypedDict's
        __optional_keys__ attribute to check if a field_name is optional.

    """

    entity_description: T
    output_type: OutputType
    direction: str | None = None
    time_series: bool = False
    default: float | bool | None = None


# Type alias for flat input fields: field_name -> field_info
type FlatInputFields = dict[str, InputFieldInfo[Any]]

# Type alias for grouped input fields: section_key -> field_name -> field_info
type GroupedInputFields = dict[str, dict[str, InputFieldInfo[Any]]]


def flatten_input_fields(grouped_fields: GroupedInputFields) -> FlatInputFields:
    """Flatten grouped input fields to a flat dict.

    Args:
        grouped_fields: Dictionary mapping section keys to field dicts.

    Returns:
        Flat dict mapping field names to input field infos.

    """
    result: dict[str, InputFieldInfo[Any]] = {}
    for fields in grouped_fields.values():
        result.update(fields)
    return result


__all__ = [
    "FlatInputFields",
    "GroupedInputFields",
    "InputFieldInfo",
    "flatten_input_fields",
]
