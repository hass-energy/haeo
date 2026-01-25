"""Inverter element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "inverter"

# Configuration field names
CONF_CONNECTION: Final = "connection"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"
CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_MAX_POWER_DC_TO_AC: Final = "max_power_dc_to_ac"
CONF_MAX_POWER_AC_TO_DC: Final = "max_power_ac_to_dc"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_LIMITS: Final = "limits"
CONF_SECTION_ADVANCED: Final = "advanced"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_EFFICIENCY_DC_TO_AC, CONF_EFFICIENCY_AC_TO_DC})


class InverterBasicConfig(TypedDict):
    """Basic configuration for inverter elements."""

    name: str
    connection: str  # AC side node to connect to


class InverterLimitsConfig(TypedDict):
    """Limits configuration for inverter elements."""

    max_power_dc_to_ac: str | float  # Entity ID or constant kW
    max_power_ac_to_dc: str | float  # Entity ID or constant kW


class InverterAdvancedConfig(TypedDict, total=False):
    """Advanced configuration for inverter elements."""

    efficiency_dc_to_ac: str | float  # Entity ID or constant %
    efficiency_ac_to_dc: str | float  # Entity ID or constant %


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - str: Entity ID when linking to a sensor
    - float: Constant value when using HAEO Configurable
    - NotRequired: Field not present when using default
    """

    element_type: Literal["inverter"]
    basic: InverterBasicConfig
    limits: InverterLimitsConfig
    advanced: InverterAdvancedConfig


class InverterBasicData(TypedDict):
    """Loaded basic values for inverter elements."""

    name: str
    connection: str  # AC side node to connect to


class InverterLimitsData(TypedDict):
    """Loaded limit values for inverter elements."""

    max_power_dc_to_ac: NDArray[np.floating[Any]] | float  # Loaded power limit per period (kW)
    max_power_ac_to_dc: NDArray[np.floating[Any]] | float  # Loaded power limit per period (kW)


class InverterAdvancedData(TypedDict, total=False):
    """Loaded advanced values for inverter elements."""

    efficiency_dc_to_ac: NDArray[np.floating[Any]] | float  # Ratio (0-1), defaults to 1.0 (no loss)
    efficiency_ac_to_dc: NDArray[np.floating[Any]] | float  # Ratio (0-1), defaults to 1.0 (no loss)


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["inverter"]
    basic: InverterBasicData
    limits: InverterLimitsData
    advanced: InverterAdvancedData
