"""Inverter element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_ADVANCED,
    SECTION_DETAILS,
    SECTION_POWER_LIMITS,
    AdvancedConfig,
    AdvancedData,
    ConnectedDetailsConfig,
    ConnectedDetailsData,
    PowerLimitsPairConfig,
    PowerLimitsPairData,
)

ELEMENT_TYPE: Final = "inverter"

CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_EFFICIENCY_DC_TO_AC, CONF_EFFICIENCY_AC_TO_DC})


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant."""

    element_type: Literal["inverter"]
    details: ConnectedDetailsConfig
    power_limits: PowerLimitsPairConfig
    advanced: AdvancedConfig


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values."""

    element_type: Literal["inverter"]
    details: ConnectedDetailsData
    power_limits: PowerLimitsPairData
    advanced: AdvancedData


__all__ = [
    "CONF_EFFICIENCY_AC_TO_DC",
    "CONF_EFFICIENCY_DC_TO_AC",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_DETAILS",
    "SECTION_POWER_LIMITS",
    "InverterConfigData",
    "InverterConfigSchema",
]
