"""Shared definitions for efficiency configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_EFFICIENCY: Final = "efficiency"

type EfficiencyValueConfig = str | float
type EfficiencyValueData = NDArray[np.floating[Any]] | float


class EfficiencyConfig(TypedDict, total=False):
    """Efficiency configuration across element types."""

    efficiency: EfficiencyValueConfig
    efficiency_ac_to_dc: EfficiencyValueConfig
    efficiency_dc_to_ac: EfficiencyValueConfig
    efficiency_source_target: EfficiencyValueConfig
    efficiency_target_source: EfficiencyValueConfig


class EfficiencyData(TypedDict, total=False):
    """Loaded efficiency values across element types."""

    efficiency: EfficiencyValueData
    efficiency_ac_to_dc: EfficiencyValueData
    efficiency_dc_to_ac: EfficiencyValueData
    efficiency_source_target: EfficiencyValueData
    efficiency_target_source: EfficiencyValueData


def efficiency_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard efficiency section definition."""
    return SectionDefinition(key=SECTION_EFFICIENCY, fields=fields, collapsed=collapsed)


def build_efficiency_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build efficiency field entries for config flows."""
    return {}


__all__ = [
    "SECTION_EFFICIENCY",
    "EfficiencyConfig",
    "EfficiencyData",
    "build_efficiency_fields",
    "efficiency_section",
]
