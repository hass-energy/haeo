"""Shared definitions for pricing configuration sections."""

from typing import Final

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_PRICING: Final = "pricing"


def pricing_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard pricing section definition."""
    return SectionDefinition(key=SECTION_PRICING, fields=fields, collapsed=collapsed)


__all__ = ["SECTION_PRICING", "pricing_section"]
