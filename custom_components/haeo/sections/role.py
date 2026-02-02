"""Shared definitions for role configuration sections."""

from typing import Any, Final, TypedDict

import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_ROLE: Final = "role"


class RoleConfig(TypedDict, total=False):
    """Role configuration for node behavior."""

    is_source: bool
    is_sink: bool


class RoleData(TypedDict, total=False):
    """Loaded role values for node behavior."""

    is_source: bool
    is_sink: bool


def role_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard role section definition."""
    return SectionDefinition(key=SECTION_ROLE, fields=fields, collapsed=collapsed)


def build_role_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build role field entries for config flows."""
    return {}


__all__ = [
    "SECTION_ROLE",
    "RoleConfig",
    "RoleData",
    "build_role_fields",
    "role_section",
]
