"""Input field metadata for creating input entities.

Defines which config fields should become input entities (NumberEntity/SwitchEntity)
and their associated metadata like units, limits, and device classes.
"""

from dataclasses import dataclass
from enum import Enum

from homeassistant.components.number import NumberDeviceClass


class InputEntityType(Enum):
    """Type of input entity to create."""

    NUMBER = "number"
    SWITCH = "switch"


@dataclass(frozen=True, slots=True)
class InputFieldInfo:
    """Metadata for a config field that becomes an input entity.

    Attributes:
        field_name: The key in the element's ConfigSchema
        entity_type: Whether this becomes a NumberEntity or SwitchEntity
        output_type: From model.const OUTPUT_TYPE_* for categorization
        unit: Native unit of measurement
        min_value: Minimum allowed value (for numbers)
        max_value: Maximum allowed value (for numbers)
        step: Step size for UI (for numbers)
        device_class: Home Assistant device class
        translation_key: Override translation key if different from field_name
        direction: "+" or "-" for power direction attributes
        time_series: Whether this field is time series (list) or scalar

    """

    field_name: str
    entity_type: InputEntityType
    output_type: str
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    device_class: NumberDeviceClass | None = None
    translation_key: str | None = None
    direction: str | None = None
    time_series: bool = False


__all__ = [
    "InputEntityType",
    "InputFieldInfo",
]
