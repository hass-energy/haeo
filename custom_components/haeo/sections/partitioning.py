"""Shared definitions for partitioning configuration sections."""

from typing import Any, Final, TypedDict

import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_PARTITIONING: Final = "partitioning"


class PartitioningConfig(TypedDict, total=False):
    """Partitioning configuration values."""

    configure_partitions: bool


class PartitioningData(TypedDict, total=False):
    """Loaded partitioning values."""

    configure_partitions: bool


def partitioning_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard partitioning section definition."""
    return SectionDefinition(key=SECTION_PARTITIONING, fields=fields, collapsed=collapsed)


def build_partitioning_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build partitioning field entries for config flows."""
    return {}


__all__ = [
    "SECTION_PARTITIONING",
    "PartitioningConfig",
    "PartitioningData",
    "build_partitioning_fields",
    "partitioning_section",
]
