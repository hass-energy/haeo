"""Shared definitions for efficiency configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_EFFICIENCY: Final = "efficiency"

CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"

type EfficiencyValueConfig = str | float
type EfficiencyValueData = NDArray[np.floating[Any]] | float


class EfficiencyConfig(TypedDict, total=False):
    """Efficiency configuration across element types."""

    efficiency_source_target: EfficiencyValueConfig
    efficiency_target_source: EfficiencyValueConfig


class EfficiencyData(TypedDict, total=False):
    """Loaded efficiency values across element types."""

    efficiency_source_target: EfficiencyValueData
    efficiency_target_source: EfficiencyValueData


def efficiency_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard efficiency section definition."""
    return SectionDefinition(key=SECTION_EFFICIENCY, fields=fields, collapsed=collapsed)


def build_efficiency_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build efficiency field entries for config flows."""
    return {}


__all__ = [
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "SECTION_EFFICIENCY",
    "EfficiencyConfig",
    "EfficiencyData",
    "build_efficiency_fields",
    "efficiency_section",
]
