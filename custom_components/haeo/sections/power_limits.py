"""Shared definitions for power limit configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

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


class PowerLimitsPairConfig(TypedDict):
    """Directional power limits with required entries."""

    max_power_source_target: PowerLimitValueConfig
    max_power_target_source: PowerLimitValueConfig


class PowerLimitsPairData(TypedDict):
    """Loaded directional power limits with required entries."""

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


def build_power_limits_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build power limits field entries for config flows."""
    return {}


__all__ = [
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "SECTION_POWER_LIMITS",
    "PowerLimitsConfig",
    "PowerLimitsData",
    "PowerLimitsPairConfig",
    "PowerLimitsPairData",
    "build_power_limits_fields",
    "power_limits_section",
]
