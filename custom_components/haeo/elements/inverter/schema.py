"""Inverter element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
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

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE}
)


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
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
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
