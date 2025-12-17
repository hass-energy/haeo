"""Input field metadata extraction for runtime configuration entities.

This module provides utilities to extract input field information from element
ConfigSchema types. Input fields are constant fields (not sensors) that can be
exposed as Number or Switch entities for runtime configuration.

The information extracted includes:
- Field name and type (number vs switch)
- Unit of measurement
- Min/max/step values for number entities
- Device class for proper entity behavior
"""

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Annotated, get_args, get_origin, get_type_hints

from homeassistant.components.number import NumberDeviceClass

from .fields import (
    BATTERY_UNITS,
    ENERGY_UNITS,
    PERCENTAGE_UNITS,
    POWER_UNITS,
    PRICE_UNITS,
    BatterySOCFieldMeta,
    BooleanFieldMeta,
    EnergyFieldMeta,
    FieldMeta,
    PercentageFieldMeta,
    PowerFieldMeta,
    PowerFlowFieldMeta,
    PriceFieldMeta,
    SensorFieldMeta,
)

if TYPE_CHECKING:
    from custom_components.haeo.elements import ElementType


class InputEntityType(StrEnum):
    """Type of input entity to create for a field."""

    NUMBER = auto()
    SWITCH = auto()


@dataclass(frozen=True, slots=True)
class InputFieldInfo:
    """Metadata for creating an input entity from a config field.

    Attributes:
        field_name: Name of the field in the config schema
        entity_type: Whether to create a Number or Switch entity
        unit: Unit of measurement (for Number entities)
        min_value: Minimum allowed value (for Number entities)
        max_value: Maximum allowed value (for Number entities)
        step: Step size for value changes (for Number entities)
        device_class: Device class for entity behavior
        translation_key: Translation key for entity name

    """

    field_name: str
    entity_type: InputEntityType
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    device_class: NumberDeviceClass | None = None
    translation_key: str | None = None


# Field meta types that produce Number entities
NUMBER_FIELD_METAS: tuple[type[FieldMeta], ...] = (
    PowerFieldMeta,
    PowerFlowFieldMeta,
    EnergyFieldMeta,
    PriceFieldMeta,
    PercentageFieldMeta,
    BatterySOCFieldMeta,
)

# Field meta types that produce Switch entities
SWITCH_FIELD_METAS: tuple[type[FieldMeta], ...] = (BooleanFieldMeta,)

# Fields to skip - metadata fields that are not input entities
SKIP_FIELDS: frozenset[str] = frozenset(
    {
        "element_type",
        "name",
        "connection",  # Element name selector, not a runtime input
    }
)


def _extract_field_meta(field_type: type) -> FieldMeta | None:
    """Extract FieldMeta from a type annotation."""
    # Handle NotRequired wrapper
    origin = get_origin(field_type)
    if origin is not None and hasattr(origin, "__name__") and origin.__name__ == "NotRequired":
        field_type = get_args(field_type)[0]

    # Extract FieldMeta from Annotated type
    if get_origin(field_type) is Annotated:
        for meta in field_type.__metadata__:
            if isinstance(meta, FieldMeta):
                return meta

    return None


def _field_meta_to_input_info(field_name: str, meta: FieldMeta, element_type: str) -> InputFieldInfo | None:
    """Convert a FieldMeta to InputFieldInfo if it should be an input entity.

    Almost all fields become input entities. The mode (DRIVEN vs EDITABLE) is
    determined at runtime based on whether the user provided an entity ID.
    """
    # Handle constant field types (have explicit device_class, unit, min/max)
    if isinstance(meta, NUMBER_FIELD_METAS):
        return InputFieldInfo(
            field_name=field_name,
            entity_type=InputEntityType.NUMBER,
            unit=meta.unit,
            min_value=meta.min,
            max_value=meta.max,
            step=meta.step,
            device_class=meta.device_class,
            translation_key=f"{element_type}_{field_name}",
        )

    if isinstance(meta, SWITCH_FIELD_METAS):
        return InputFieldInfo(
            field_name=field_name,
            entity_type=InputEntityType.SWITCH,
            translation_key=f"{element_type}_{field_name}",
        )

    # Handle sensor field types - map accepted_units to device class
    if isinstance(meta, SensorFieldMeta):
        return _sensor_meta_to_input_info(field_name, meta, element_type)

    return None


def _sensor_meta_to_input_info(field_name: str, meta: SensorFieldMeta, element_type: str) -> InputFieldInfo | None:
    """Convert a SensorFieldMeta to InputFieldInfo.

    Maps the accepted_units to appropriate device class and unit.
    """
    accepted = meta.accepted_units

    # Power sensor
    if accepted is POWER_UNITS or accepted == POWER_UNITS:
        return InputFieldInfo(
            field_name=field_name,
            entity_type=InputEntityType.NUMBER,
            unit="kW",
            device_class=NumberDeviceClass.POWER,
            translation_key=f"{element_type}_{field_name}",
        )

    # Energy sensor
    if accepted is ENERGY_UNITS or accepted == ENERGY_UNITS:
        return InputFieldInfo(
            field_name=field_name,
            entity_type=InputEntityType.NUMBER,
            unit="kWh",
            device_class=NumberDeviceClass.ENERGY,
            translation_key=f"{element_type}_{field_name}",
        )

    # Battery SOC sensor (percentage for battery)
    if accepted == BATTERY_UNITS:
        return InputFieldInfo(
            field_name=field_name,
            entity_type=InputEntityType.NUMBER,
            unit="%",
            min_value=0.0,
            max_value=100.0,
            device_class=NumberDeviceClass.BATTERY,
            translation_key=f"{element_type}_{field_name}",
        )

    # Percentage sensor
    if accepted == PERCENTAGE_UNITS:
        return InputFieldInfo(
            field_name=field_name,
            entity_type=InputEntityType.NUMBER,
            unit="%",
            min_value=0.0,
            max_value=100.0,
            device_class=None,
            translation_key=f"{element_type}_{field_name}",
        )

    # Price sensor (currency per energy)
    if accepted == PRICE_UNITS:
        return InputFieldInfo(
            field_name=field_name,
            entity_type=InputEntityType.NUMBER,
            unit="$/kWh",
            device_class=NumberDeviceClass.MONETARY,
            translation_key=f"{element_type}_{field_name}",
        )

    # Unknown sensor type - skip
    return None


def get_input_fields(element_type: "ElementType") -> list[InputFieldInfo]:
    """Get input field metadata for an element type.

    Extracts all numeric and boolean fields from the element's ConfigSchema
    that should become Number or Switch entities for runtime configuration.

    Each field can operate in two modes:
    - DRIVEN: User provided an entity ID, input entity mirrors that entity
    - EDITABLE: User provided no entity ID, input entity is user-controlled

    Args:
        element_type: The element type to get input fields for

    Returns:
        List of InputFieldInfo for each field that should become an input entity

    """
    # Import here to avoid circular import
    from custom_components.haeo.elements import ELEMENT_TYPES  # noqa: PLC0415

    registry_entry = ELEMENT_TYPES[element_type]
    schema_class = registry_entry.schema

    hints = get_type_hints(schema_class, include_extras=True)
    input_fields: list[InputFieldInfo] = []

    for field_name, field_type in hints.items():
        # Skip metadata fields
        if field_name in SKIP_FIELDS:
            continue

        # Extract field meta from annotation
        meta = _extract_field_meta(field_type)
        if meta is None:
            continue

        # Convert to input info if applicable
        info = _field_meta_to_input_info(field_name, meta, element_type)
        if info is not None:
            input_fields.append(info)

    return input_fields


def get_all_input_fields() -> dict["ElementType", list[InputFieldInfo]]:
    """Get input field metadata for all element types.

    Returns:
        Dict mapping element type to list of input fields

    """
    # Import here to avoid circular import
    from custom_components.haeo.elements import ELEMENT_TYPES  # noqa: PLC0415

    return {element_type: get_input_fields(element_type) for element_type in ELEMENT_TYPES}


__all__ = [
    "InputEntityType",
    "InputFieldInfo",
    "get_all_input_fields",
    "get_input_fields",
]
