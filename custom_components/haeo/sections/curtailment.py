"""Flow builders for curtailment configuration sections."""

from custom_components.haeo.core.schema.sections.curtailment import SECTION_CURTAILMENT
from custom_components.haeo.flows.field_schema import SectionDefinition


def curtailment_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard curtailment section definition."""
    return SectionDefinition(key=SECTION_CURTAILMENT, fields=fields, collapsed=collapsed)


__all__ = [
    "curtailment_section",
]
