"""Shared definitions for power limit configuration sections."""

from collections.abc import Mapping
from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries

SECTION_POWER_LIMITS: Final = "power_limits"
CONF_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONF_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"

type PowerLimitValueConfig = str | float
type PowerLimitValueData = NDArray[np.floating[Any]] | float


class PowerLimitsConfig(TypedDict, total=False):
    """Directional power limit configuration."""

    max_power_source_target: PowerLimitValueConfig
    max_power_target_source: PowerLimitValueConfig


class PowerLimitsData(TypedDict, total=False):
    """Loaded directional power limits."""

    max_power_source_target: PowerLimitValueData
    max_power_target_source: PowerLimitValueData


def power_limits_section(
    fields: tuple[str, ...],
    *,
    key: str = SECTION_POWER_LIMITS,
    collapsed: bool = False,
) -> SectionDefinition:
    """Return the standard power limits section definition."""
    return SectionDefinition(key=key, fields=fields, collapsed=collapsed)


def build_power_limits_fields(
    input_fields: InputFieldSection,
    *,
    optional_fields: frozenset[str],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build power limits field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        optional_fields=optional_fields,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "SECTION_POWER_LIMITS",
    "PowerLimitsConfig",
    "PowerLimitsData",
    "build_power_limits_fields",
    "power_limits_section",
]
