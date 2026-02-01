"""Shared definitions for advanced configuration sections."""

from typing import Final

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_ADVANCED: Final = "advanced"


def advanced_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard advanced section definition."""
    return SectionDefinition(key=SECTION_ADVANCED, fields=fields, collapsed=collapsed)


__all__ = ["SECTION_ADVANCED", "advanced_section"]
