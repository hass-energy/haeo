"""Flow builders for curtailment configuration sections."""

import voluptuous as vol

from custom_components.haeo.core.schema.sections.curtailment import SECTION_CURTAILMENT
from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries


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
    "build_curtailment_fields",
    "curtailment_section",
]
