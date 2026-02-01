"""Shared definitions for storage configuration sections."""

from typing import Final

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_STORAGE: Final = "storage"
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"


def storage_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard storage section definition."""
    return SectionDefinition(key=SECTION_STORAGE, fields=fields, collapsed=collapsed)


__all__ = [
    "CONF_CAPACITY",
    "CONF_INITIAL_CHARGE",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "SECTION_STORAGE",
    "storage_section",
]
