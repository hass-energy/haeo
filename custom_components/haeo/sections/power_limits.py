"""Flow builders for power limit configuration sections."""

from custom_components.haeo.core.schema.sections.power_limits import SECTION_POWER_LIMITS
from custom_components.haeo.flows.field_schema import SectionDefinition


def power_limits_section(
    fields: tuple[str, ...],
    *,
    key: str = SECTION_POWER_LIMITS,
    collapsed: bool = False,
) -> SectionDefinition:
    """Return the standard power limits section definition."""
    return SectionDefinition(key=key, fields=fields, collapsed=collapsed)


__all__ = [
    "power_limits_section",
]
