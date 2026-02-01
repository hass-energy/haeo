"""Inverter element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    SECTION_ADVANCED,
    SECTION_DETAILS,
    SECTION_LIMITS,
    AdvancedConfig,
    AdvancedData,
    DetailsConfig,
    DetailsData,
    LimitsConfig,
    LimitsData,
)

ELEMENT_TYPE: Final = "inverter"

CONF_MAX_POWER_AC_TO_DC: Final = "max_power_ac_to_dc"
CONF_MAX_POWER_DC_TO_AC: Final = "max_power_dc_to_ac"

CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_EFFICIENCY_DC_TO_AC, CONF_EFFICIENCY_AC_TO_DC})


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant."""

    element_type: Literal["inverter"]
    basic: DetailsConfig
    limits: LimitsConfig
    advanced: AdvancedConfig


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values."""

    element_type: Literal["inverter"]
    basic: DetailsData
    limits: LimitsData
    advanced: AdvancedData


__all__ = [
    "CONF_EFFICIENCY_AC_TO_DC",
    "CONF_EFFICIENCY_DC_TO_AC",
    "CONF_MAX_POWER_AC_TO_DC",
    "CONF_MAX_POWER_DC_TO_AC",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_DETAILS",
    "SECTION_LIMITS",
    "InverterConfigData",
    "InverterConfigSchema",
]
