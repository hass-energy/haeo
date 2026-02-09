"""Shared definitions for curtailment-style boolean control sections.

This section is used by elements where a forecast can be treated as either:
- fixed (must be followed exactly), or
- flexible (can be reduced/curtailed/shedded if economically sensible).
"""

from typing import Final, TypedDict

import voluptuous as vol

from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries
from custom_components.haeo.schema import ConstantValue, EntityValue

SECTION_CURTAILMENT: Final = "curtailment"

CONF_CURTAILMENT: Final = "curtailment"


class CurtailmentConfig(TypedDict, total=False):
    """Curtailment configuration values."""

    curtailment: EntityValue | ConstantValue


class CurtailmentData(TypedDict, total=False):
    """Loaded curtailment values."""

    curtailment: bool


def curtailment_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard curtailment section definition."""
    return SectionDefinition(key=SECTION_CURTAILMENT, fields=fields, collapsed=collapsed)


def build_curtailment_fields(
    input_fields: InputFieldSection,
    *,
    field_schema: dict[str, FieldSchemaInfo],
    inclusion_map: dict[str, list[str]],
    current_data: dict[str, object] | None = None,
) -> dict[str, tuple[vol.Marker, object]]:
    """Build curtailment field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        field_schema=field_schema,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "CONF_CURTAILMENT",
    "SECTION_CURTAILMENT",
    "CurtailmentConfig",
    "CurtailmentData",
    "build_curtailment_fields",
    "curtailment_section",
]

