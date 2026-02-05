"""Shared definitions for efficiency configuration sections."""

from collections.abc import Mapping
from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.elements import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries
from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue

SECTION_EFFICIENCY: Final = "efficiency"

CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"

type EfficiencyValueConfig = EntityValue | ConstantValue | NoneValue
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


def build_efficiency_fields(
    input_fields: InputFieldSection,
    *,
    field_schema: Mapping[str, FieldSchemaInfo],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build efficiency field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        field_schema=field_schema,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "SECTION_EFFICIENCY",
    "EfficiencyConfig",
    "EfficiencyData",
    "build_efficiency_fields",
    "efficiency_section",
]
