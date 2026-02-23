"""Flow builders for efficiency configuration sections."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.haeo.core.schema.sections.efficiency import SECTION_EFFICIENCY
from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries


def efficiency_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard efficiency section definition."""
    return SectionDefinition(key=SECTION_EFFICIENCY, fields=fields, collapsed=collapsed)


def build_efficiency_fields(
    input_fields: InputFieldSection,
    *,
    field_schema: Mapping[str, FieldSchemaInfo],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build efficiency field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        field_schema=field_schema,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "build_efficiency_fields",
    "efficiency_section",
]
