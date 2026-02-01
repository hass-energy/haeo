"""Shared definitions for limits configuration sections."""

from typing import Final

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_LIMITS: Final = "limits"


def limits_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard limits section definition."""
    return SectionDefinition(key=SECTION_LIMITS, fields=fields, collapsed=collapsed)


__all__ = ["SECTION_LIMITS", "limits_section"]
