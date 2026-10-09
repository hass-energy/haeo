"""Flow builders for power limit configuration sections."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.haeo.core.schema.sections.power_limits import SECTION_POWER_LIMITS
from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries


def power_limits_section(
    fields: tuple[str, ...],
    *,
    key: str = SECTION_POWER_LIMITS,
    collapsed: bool = False,
) -> SectionDefinition:
    """Return the standard power limits section definition."""
    return SectionDefinition(key=key, fields=fields, collapsed=collapsed)


def build_power_limits_fields(
    input_fields: InputFieldSection,
    *,
    field_schema: Mapping[str, FieldSchemaInfo],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build power limits field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        field_schema=field_schema,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "build_power_limits_fields",
    "power_limits_section",
]
