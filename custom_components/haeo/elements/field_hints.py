"""Transforms schema-level field hints into HA input field metadata.

Provides default HA entity descriptions (units, min/max/step, device classes)
based on OutputType, and a builder to instantiate them using declarative hints.
"""

from dataclasses import dataclass
from typing import Annotated, Any, NotRequired, Required, get_args, get_origin, get_type_hints

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.helpers.entity import EntityDescription

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.units import UnitOfMeasurement
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo


@dataclass(frozen=True, slots=True)
class OutputTypeMetadata:
    """Default metadata for creating NumberEntityDescription for an OutputType."""

    unit: str | None
    device_class: str | None
    min_value: float
    max_value: float
    step: float


OUTPUT_TYPE_DEFAULTS: dict[OutputType, OutputTypeMetadata] = {
    OutputType.POWER: OutputTypeMetadata(
        unit=UnitOfMeasurement.KILO_WATT,
        device_class=NumberDeviceClass.POWER,
        min_value=0.0,
        max_value=1000.0,
        step=0.01,
    ),
    OutputType.POWER_LIMIT: OutputTypeMetadata(
        unit=UnitOfMeasurement.KILO_WATT,
        device_class=NumberDeviceClass.POWER,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
    ),
    OutputType.ENERGY: OutputTypeMetadata(
        unit=UnitOfMeasurement.KILO_WATT_HOUR,
        device_class=NumberDeviceClass.ENERGY_STORAGE,
        min_value=0.1,
        max_value=1000.0,
        step=0.1,
    ),
    OutputType.STATE_OF_CHARGE: OutputTypeMetadata(
        unit=UnitOfMeasurement.PERCENT,
        device_class=NumberDeviceClass.BATTERY,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
    ),
    OutputType.EFFICIENCY: OutputTypeMetadata(
        unit=UnitOfMeasurement.PERCENT,
        device_class=NumberDeviceClass.POWER_FACTOR,
        min_value=50.0,
        max_value=100.0,
        step=0.1,
    ),
    OutputType.PRICE: OutputTypeMetadata(
        unit=None,
        device_class=None,
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
    ),
}


def build_input_fields(
    element_type: str,
    field_hints: dict[str, dict[str, FieldHint]],
) -> dict[str, dict[str, InputFieldInfo[Any]]]:
    """Transform schema field hints into full HA InputFieldInfo objects."""
    result: dict[str, dict[str, InputFieldInfo[Any]]] = {}

    for section_name, fields in field_hints.items():
        result[section_name] = {}
        for field_name, hint in fields.items():
            # Build HA entity description
            key = field_name
            translation_key = f"{element_type}_{field_name}"

            if hint.output_type == OutputType.STATUS:
                entity_description: EntityDescription = SwitchEntityDescription(
                    key=key,
                    translation_key=translation_key,
                )
            else:
                defaults = OUTPUT_TYPE_DEFAULTS[hint.output_type]
                entity_description = NumberEntityDescription(
                    key=key,
                    translation_key=translation_key,
                    native_unit_of_measurement=defaults.unit,
                    device_class=defaults.device_class,  # type: ignore[reportArgumentType]
                    native_min_value=hint.min_value if hint.min_value is not None else defaults.min_value,
                    native_max_value=hint.max_value if hint.max_value is not None else defaults.max_value,
                    native_step=hint.step if hint.step is not None else defaults.step,
                )

            # Build optional defaults
            input_defaults = None
            if hint.default_mode is not None or hint.default_value is not None:
                input_defaults = InputFieldDefaults(
                    mode=hint.default_mode,
                    value=hint.default_value,
                )

            result[section_name][field_name] = InputFieldInfo(
                field_name=field_name,
                entity_description=entity_description,  # type: ignore[reportArgumentType]
                output_type=hint.output_type,
                direction=hint.direction,
                time_series=hint.time_series,
                boundaries=hint.boundaries,
                defaults=input_defaults,
                force_required=hint.force_required,
                device_type=hint.device_type,
            )

    return result


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
