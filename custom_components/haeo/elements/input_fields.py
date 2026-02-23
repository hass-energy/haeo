"""Input field metadata for creating input entities.

Defines which config fields should become input entities (NumberEntity/SwitchEntity)
and their associated metadata like output type, direction, and time series behavior.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription

from custom_components.haeo.core.model.const import OutputType


@dataclass(frozen=True, slots=True)
class InputFieldDefaults:
    """Default pre-selection behavior for config flow fields.

    Attributes:
        mode: Controls what is pre-selected in step 1:
            - 'entity': Pre-select the entity specified in `entity`
            - 'value': Pre-select the HAEO Configurable sentinel entity
            - None: No pre-selection (empty)
        entity: Entity ID to pre-select when mode='entity'
        value: Value to pre-fill in step 2 when mode='value'

    Note:
        When mode='value', step 2 is always Required. The value is only
        used for pre-filling the form, not as a fallback. If the user
        clears step 1 selection, the field is omitted from config.

    """

    mode: Literal["entity", "value"] | None = None
    entity: str | None = None
    value: float | bool | None = None


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
        defaults: Default pre-selection behavior for config flow fields
        device_type: Optional device type override for sub-device inputs

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
    defaults: InputFieldDefaults | None = None
    # Force value to be required, even if its optional in the schema
    force_required: bool | None = None
    # Optional device type for sub-device association
    device_type: str | None = None


type InputFieldSection = Mapping[str, InputFieldInfo[Any]]
type InputFieldGroups = Mapping[str, InputFieldSection]
type InputFieldPath = tuple[str, ...]

__all__ = [
    "InputFieldDefaults",
    "InputFieldGroups",
    "InputFieldInfo",
    "InputFieldPath",
    "InputFieldSection",
]
