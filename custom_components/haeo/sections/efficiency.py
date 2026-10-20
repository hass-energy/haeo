"""Flow builders for efficiency configuration sections."""

from custom_components.haeo.core.schema.sections.efficiency import SECTION_EFFICIENCY
from custom_components.haeo.flows.field_schema import SectionDefinition


def efficiency_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard efficiency section definition."""
    return SectionDefinition(key=SECTION_EFFICIENCY, fields=fields, collapsed=collapsed)


__all__ = [
    "efficiency_section",
]
