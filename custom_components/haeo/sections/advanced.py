"""Shared definitions for advanced configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_ADVANCED: Final = "advanced"

type AdvancedValueConfig = str | float
type AdvancedValueData = NDArray[np.floating[Any]] | float


class AdvancedConfig(TypedDict, total=False):
    """Advanced configuration across element types."""

    efficiency: AdvancedValueConfig
    configure_partitions: bool
    curtailment: str | bool
    is_source: bool
    is_sink: bool
    efficiency_ac_to_dc: AdvancedValueConfig
    efficiency_dc_to_ac: AdvancedValueConfig
    efficiency_source_target: AdvancedValueConfig
    efficiency_target_source: AdvancedValueConfig


class AdvancedData(TypedDict, total=False):
    """Loaded advanced values across element types."""

    efficiency: AdvancedValueData
    configure_partitions: bool
    curtailment: bool
    is_source: bool
    is_sink: bool
    efficiency_ac_to_dc: AdvancedValueData
    efficiency_dc_to_ac: AdvancedValueData
    efficiency_source_target: AdvancedValueData
    efficiency_target_source: AdvancedValueData


def advanced_section(fields: tuple[str, ...], *, collapsed: bool = True) -> SectionDefinition:
    """Return the standard advanced section definition."""
    return SectionDefinition(key=SECTION_ADVANCED, fields=fields, collapsed=collapsed)


def build_advanced_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build advanced field entries for config flows."""
    return {}


__all__ = [  # noqa: RUF022
    "AdvancedConfig",
    "AdvancedData",
    "SECTION_ADVANCED",
    "advanced_section",
    "build_advanced_fields",
]
