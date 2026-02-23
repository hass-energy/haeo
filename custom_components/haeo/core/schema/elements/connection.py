"""Connection element schema definitions."""

from typing import Annotated, Final, Literal, TypedDict

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConnectionTarget
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    CommonConfig,
    CommonData,
    EfficiencyConfig,
    EfficiencyData,
    PowerLimitsConfig,
    PowerLimitsData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE = ElementType.CONNECTION

SECTION_ENDPOINTS: Final = "endpoints"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_EFFICIENCY_SOURCE_TARGET,
        CONF_EFFICIENCY_TARGET_SOURCE,
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
    }
)


class EndpointsConfig(TypedDict):
    """Endpoint configuration for source/target pairs."""

    source: ConnectionTarget
    target: ConnectionTarget


class EndpointsData(TypedDict):
    """Loaded endpoint values."""

    source: ConnectionTarget
    target: ConnectionTarget


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.CONNECTION]
    common: CommonConfig
    endpoints: EndpointsConfig
    power_limits: Annotated[
        PowerLimitsConfig,
        SectionHints(
            {
                CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    time_series=True,
                ),
                CONF_MAX_POWER_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    time_series=True,
                ),
            }
        ),
    ]
    pricing: Annotated[
        PricingConfig,
        SectionHints(
            {
                CONF_PRICE_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.PRICE,
                    direction="-",
                    time_series=True,
                ),
                CONF_PRICE_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.PRICE,
                    direction="-",
                    time_series=True,
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
                    time_series=True,
                ),
                CONF_EFFICIENCY_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.EFFICIENCY,
                    time_series=True,
                ),
            }
        ),
    ]


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values."""

    element_type: Literal[ElementType.CONNECTION]
    common: CommonData
    endpoints: EndpointsData
    power_limits: PowerLimitsData
    pricing: PricingData
    efficiency: EfficiencyData


__all__ = [
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_SOURCE",
    "CONF_TARGET",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_EFFICIENCY",
    "SECTION_ENDPOINTS",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
    "EndpointsConfig",
    "EndpointsData",
]
