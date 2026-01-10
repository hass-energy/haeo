"""Input field metadata for creating input entities.

Defines which config fields should become input entities (NumberEntity/SwitchEntity)
and their associated metadata like output type, direction, and time series behavior.
"""

from dataclasses import dataclass

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription

from custom_components.haeo.model.const import OutputType


@dataclass(frozen=True, slots=True)
class InputFieldInfo[T: (NumberEntityDescription, SwitchEntityDescription)]:
    """Metadata for a config field that becomes an input entity.

    Attributes:
        field_name: The key in the element's ConfigSchema
        entity_description: Home Assistant entity description (Number or Switch)
        output_type: OutputType enum value for categorization and unit spec lookup
        direction: "+" or "-" for power direction attributes
        time_series: Whether this field is time series (list) or scalar
        boundaries: Whether time series values are at boundaries (n+1 values) vs intervals (n values)
        default: Default value for editable entities when no restored state exists
        device_name: Device name for sub-device association. If None, uses main element device.
            For partition-specific inputs (e.g., undercharge cost), set to the partition's
            device name like "battery_device_undercharge".

    Note:
        Whether a field is optional (can be disabled in config flow) is determined
        by the element's ConfigSchema TypedDict using NotRequired. Use the TypedDict's
        __optional_keys__ attribute to check if a field_name is optional.

    """

    field_name: str
    entity_description: T
    output_type: OutputType
    direction: str | None = None
    time_series: bool = False
    boundaries: bool = False
    default: float | bool | None = None
    device_name: str | None = None


__all__ = [
    "InputFieldInfo",
]
