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
    """Charge percentage limits configuration."""

    min_charge_percentage: LimitsValueConfig
    max_charge_percentage: LimitsValueConfig


class LimitsData(TypedDict, total=False):
    """Loaded charge percentage limits."""

    min_charge_percentage: LimitsValueData
    max_charge_percentage: LimitsValueData


def limits_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard limits section definition."""
    return SectionDefinition(key=SECTION_LIMITS, fields=fields, collapsed=collapsed)


def build_limits_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build limits field entries for config flows."""
    return {}


__all__ = [
    "SECTION_LIMITS",
    "LimitsConfig",
    "LimitsData",
    "build_limits_fields",
    "limits_section",
]
