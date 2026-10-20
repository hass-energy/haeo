"""Flow builders for pricing configuration sections."""

from custom_components.haeo.core.schema.sections.pricing import SECTION_PRICING
from custom_components.haeo.flows.field_schema import SectionDefinition


def pricing_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard pricing section definition."""
    return SectionDefinition(key=SECTION_PRICING, fields=fields, collapsed=collapsed)


__all__ = [
    "pricing_section",
]
