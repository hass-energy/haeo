"""Flow builders for forecast configuration sections."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.haeo.core.schema.sections.forecast import CONF_FORECAST, SECTION_FORECAST
from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries


def forecast_section(fields: tuple[str, ...] = (CONF_FORECAST,), *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard forecast section definition."""
    return SectionDefinition(key=SECTION_FORECAST, fields=fields, collapsed=collapsed)


def build_forecast_fields(
    input_fields: InputFieldSection,
    *,
    field_schema: Mapping[str, FieldSchemaInfo],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build forecast field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        field_schema=field_schema,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "build_forecast_fields",
    "forecast_section",
]
