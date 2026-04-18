"""Transforms schema-level field hints into HA input field metadata.

Provides default HA entity descriptions (units, min/max/step, device classes)
based on OutputType, and a builder to instantiate them using declarative hints.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints
from custom_components.haeo.core.units import UnitOfMeasurement
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo


@dataclass(frozen=True, slots=True)
class OutputTypeMetadata:
    """Default metadata for creating NumberEntityDescription for an OutputType."""

    unit: str | None
    device_class: NumberDeviceClass | None
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
            translation_key = f"{element_type}_{field_name}"
            result[section_name][field_name] = _build_field_info(field_name, hint, translation_key)

    return result


def build_list_input_fields(
    element_type: str,
    list_key: str,
    list_hints: ListFieldHints,
    items: Sequence[Any],
) -> dict[str, dict[str, InputFieldInfo[Any]]]:
    """Transform a list config field into per-item InputFieldInfo groups.

    Each item in the list that contains hinted fields gets its own section
    in the result, keyed as ``"{list_key}.{index}"``.  The field path for
    entity creation and config loading becomes
    ``(list_key, str(index), field_name)``.

    Args:
        element_type: Element type string for translation key generation.
        list_key: Config key of the list field (e.g. ``"rules"``).
        list_hints: Declarative hints for fields within list items.
        items: Actual list items from the config data.

    Returns:
        Input field groups keyed by ``"{list_key}.{index}"``.

    """
    result: dict[str, dict[str, InputFieldInfo[Any]]] = {}

    for i, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        section: dict[str, InputFieldInfo[Any]] = {}
        for field_name, hint in list_hints.fields.items():
            if field_name not in item:
                continue
            translation_key = f"{element_type}_{field_name}"
            section[field_name] = _build_field_info(field_name, hint, translation_key)

        if section:
            section_key = f"{list_key}.{i}"
            result[section_key] = section

    return result


def _build_field_info(
    field_name: str,
    hint: FieldHint,
    translation_key: str,
) -> InputFieldInfo[NumberEntityDescription] | InputFieldInfo[SwitchEntityDescription]:
    """Build an InputFieldInfo from a FieldHint."""
    input_defaults = None
    if hint.default_mode is not None or hint.default_value is not None:
        input_defaults = InputFieldDefaults(
            mode=hint.default_mode,
            value=hint.default_value,
        )

    if hint.output_type == OutputType.STATUS:
        return InputFieldInfo(
            field_name=field_name,
            entity_description=SwitchEntityDescription(
                key=field_name,
                translation_key=translation_key,
            ),
            output_type=hint.output_type,
            direction=hint.direction,
            time_series=hint.time_series,
            boundaries=hint.boundaries,
            defaults=input_defaults,
            force_required=hint.force_required,
            device_type=hint.device_type,
        )

    defaults = OUTPUT_TYPE_DEFAULTS[hint.output_type]
    return InputFieldInfo(
        field_name=field_name,
        entity_description=NumberEntityDescription(
            key=field_name,
            translation_key=translation_key,
            native_unit_of_measurement=defaults.unit,
            device_class=defaults.device_class,
            native_min_value=hint.min_value if hint.min_value is not None else defaults.min_value,
            native_max_value=hint.max_value if hint.max_value is not None else defaults.max_value,
            native_step=hint.step if hint.step is not None else defaults.step,
        ),
        output_type=hint.output_type,
        direction=hint.direction,
        time_series=hint.time_series,
        boundaries=hint.boundaries,
        defaults=input_defaults,
        force_required=hint.force_required,
        device_type=hint.device_type,
    )
