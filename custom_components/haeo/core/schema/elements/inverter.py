"""Inverter element schema definitions."""

from typing import Annotated, Final, Literal, TypedDict

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import (
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
    PowerLimitsConfig,
    PowerLimitsData,
)

ELEMENT_TYPE = ElementType.INVERTER

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE})


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.INVERTER]
    common: ConnectedCommonConfig
    power_limits: Annotated[
        PowerLimitsConfig,
        SectionHints(
            {
                CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    time_series=True,
                    force_required=True,
                ),
                CONF_MAX_POWER_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    time_series=True,
                    force_required=True,
                ),
            }
        ),
    ]
    efficiency: Annotated[
        EfficiencyConfig,
        SectionHints(
            {
                CONF_EFFICIENCY_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.EFFICIENCY,
                    default_value=100.0,
                ),
                CONF_EFFICIENCY_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.EFFICIENCY,
                    default_value=100.0,
                ),
            }
        ),
    ]


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values."""

    element_type: Literal[ElementType.INVERTER]
    common: ConnectedCommonData
    power_limits: PowerLimitsData
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
