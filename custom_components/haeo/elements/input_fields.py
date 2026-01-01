"""Input field metadata for creating input entities.

Defines which config fields should become input entities (NumberEntity/SwitchEntity)
and their associated metadata like output type, direction, and time series behavior.
"""

from dataclasses import dataclass

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription


@dataclass(frozen=True, slots=True)
class InputFieldInfo[T: (NumberEntityDescription, SwitchEntityDescription)]:
    """Metadata for a config field that becomes an input entity.

    Attributes:
        field_name: The key in the element's ConfigSchema
        entity_description: Home Assistant entity description (Number or Switch)
        output_type: From model.const OUTPUT_TYPE_* for categorization
        direction: "+" or "-" for power direction attributes
        time_series: Whether this field is time series (list) or scalar
        default: Default value for editable entities when no restored state exists

    Note:
        Whether a field is optional (can be disabled in config flow) is determined
        by the element's ConfigSchema TypedDict using NotRequired. Use the TypedDict's
        __optional_keys__ attribute to check if a field_name is optional.

    """

    field_name: str
    entity_description: T
    output_type: str
    direction: str | None = None
    time_series: bool = False
    default: float | bool | None = None


__all__ = [
    "InputFieldInfo",
]
