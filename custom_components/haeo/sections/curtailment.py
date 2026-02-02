"""Shared definitions for curtailment configuration sections."""

from typing import Any, Final, TypedDict

import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_CURTAILMENT: Final = "curtailment"

type CurtailmentValueConfig = str | bool


class CurtailmentConfig(TypedDict, total=False):
    """Curtailment configuration values."""

    curtailment: CurtailmentValueConfig


class CurtailmentData(TypedDict, total=False):
    """Loaded curtailment values."""

    curtailment: bool


def curtailment_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard curtailment section definition."""
    return SectionDefinition(key=SECTION_CURTAILMENT, fields=fields, collapsed=collapsed)


def build_curtailment_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build curtailment field entries for config flows."""
    return {}


__all__ = [
    "SECTION_CURTAILMENT",
    "CurtailmentConfig",
    "CurtailmentData",
    "build_curtailment_fields",
    "curtailment_section",
]
