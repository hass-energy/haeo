"""Inverter element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.sections import (
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_LIMITS,
    BasicNameConnectionConfig,
    BasicNameConnectionData,
)

ELEMENT_TYPE: Final = "inverter"

CONF_MAX_POWER_AC_TO_DC: Final = "max_power_ac_to_dc"
CONF_MAX_POWER_DC_TO_AC: Final = "max_power_dc_to_ac"

CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_EFFICIENCY_DC_TO_AC, CONF_EFFICIENCY_AC_TO_DC})


class InverterLimitsConfig(TypedDict):
    """AC/DC power limits configuration."""

    max_power_ac_to_dc: str | float
    max_power_dc_to_ac: str | float


class InverterLimitsData(TypedDict):
    """Loaded AC/DC power limits."""

    max_power_ac_to_dc: NDArray[np.floating[Any]] | float
    max_power_dc_to_ac: NDArray[np.floating[Any]] | float


class InverterAdvancedConfig(TypedDict, total=False):
    """Optional AC/DC efficiency configuration."""

    efficiency_ac_to_dc: str | float
    efficiency_dc_to_ac: str | float


class InverterAdvancedData(TypedDict, total=False):
    """Loaded AC/DC efficiency values."""

    efficiency_ac_to_dc: NDArray[np.floating[Any]] | float
    efficiency_dc_to_ac: NDArray[np.floating[Any]] | float


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant."""

    element_type: Literal["inverter"]
    basic: BasicNameConnectionConfig
    limits: InverterLimitsConfig
    advanced: InverterAdvancedConfig


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values."""

    element_type: Literal["inverter"]
    basic: BasicNameConnectionData
    limits: InverterLimitsData
    advanced: InverterAdvancedData


__all__ = [
    "CONF_EFFICIENCY_AC_TO_DC",
    "CONF_EFFICIENCY_DC_TO_AC",
    "CONF_MAX_POWER_AC_TO_DC",
    "CONF_MAX_POWER_DC_TO_AC",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_BASIC",
    "SECTION_LIMITS",
    "InverterConfigData",
    "InverterConfigSchema",
]
