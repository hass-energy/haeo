"""Shared definitions for limits configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_LIMITS: Final = "limits"

type LimitsValueConfig = str | float
type LimitsValueData = NDArray[np.floating[Any]] | float


class LimitsConfig(TypedDict, total=False):
    """Limit configuration across element types."""

    min_charge_percentage: LimitsValueConfig
    max_charge_percentage: LimitsValueConfig
    max_charge_power: LimitsValueConfig
    max_discharge_power: LimitsValueConfig
    import_limit: LimitsValueConfig
    export_limit: LimitsValueConfig
    max_power_source_target: LimitsValueConfig
    max_power_target_source: LimitsValueConfig
    max_power_ac_to_dc: LimitsValueConfig
    max_power_dc_to_ac: LimitsValueConfig


class LimitsData(TypedDict, total=False):
    """Loaded limit values across element types."""

    min_charge_percentage: LimitsValueData
    max_charge_percentage: LimitsValueData
    max_charge_power: LimitsValueData
    max_discharge_power: LimitsValueData
    import_limit: LimitsValueData
    export_limit: LimitsValueData
    max_power_source_target: LimitsValueData
    max_power_target_source: LimitsValueData
    max_power_ac_to_dc: LimitsValueData
    max_power_dc_to_ac: LimitsValueData


def limits_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard limits section definition."""
    return SectionDefinition(key=SECTION_LIMITS, fields=fields, collapsed=collapsed)


def build_limits_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build limits field entries for config flows."""
    return {}


__all__ = [  # noqa: RUF022
    "LimitsConfig",
    "LimitsData",
    "SECTION_LIMITS",
    "build_limits_fields",
    "limits_section",
]
