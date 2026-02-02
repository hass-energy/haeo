"""Inverter element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    ConnectedCommonConfig,
    ConnectedCommonData,
    EfficiencyConfig,
    EfficiencyData,
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
    common: ConnectedCommonConfig
    power_limits: PowerLimitsPairConfig
    efficiency: EfficiencyConfig


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values."""

    element_type: Literal["inverter"]
    common: ConnectedCommonData
    power_limits: PowerLimitsPairData
    efficiency: EfficiencyData


__all__ = [
    "CONF_EFFICIENCY_AC_TO_DC",
    "CONF_EFFICIENCY_DC_TO_AC",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_EFFICIENCY",
    "SECTION_POWER_LIMITS",
    "InverterConfigData",
    "InverterConfigSchema",
]
