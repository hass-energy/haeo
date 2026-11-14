"""Connection element schema definitions."""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConnectionTarget, ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
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
SECTION_LEVEL: Final = "level"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_CONDUCTANCE: Final = "conductance"
CONF_MAX_CONDUCTANCE: Final = "max_conductance"
CONF_DRAWS_FROM_TARGET: Final = "draws_from_target"


class EndpointsConfig(TypedDict):
    """Endpoint configuration for source/target pairs."""

    source: ConnectionTarget
    target: ConnectionTarget


class EndpointsData(TypedDict):
    """Loaded endpoint values."""

    source: ConnectionTarget
    target: ConnectionTarget


class LevelConfig(TypedDict, total=False):
    """Flow set or capped by the difference in level, such as temperature, between the endpoints."""

    conductance: EntityValue | ConstantValue | NoneValue
    max_conductance: EntityValue | ConstantValue | NoneValue


class LevelData(TypedDict, total=False):
    """Loaded level flow values."""

    conductance: NDArray[np.float64] | float
    max_conductance: NDArray[np.float64] | float


class ConnectionEfficiencyConfig(EfficiencyConfig, total=False):
    """Efficiency, and whether the flow takes energy from the target rather than adding it."""

    draws_from_target: EntityValue | ConstantValue


class ConnectionEfficiencyData(EfficiencyData, total=False):
    """Loaded efficiency values."""

    draws_from_target: bool


class ConnectionConfigSchema(CommonConfig):
    """Connection element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.CONNECTION]
    endpoints: EndpointsConfig
    power_limits: Annotated[
        PowerLimitsConfig,
        SectionHints(
            {
                CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
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
            }
        ),
    ]
    efficiency: Annotated[
        ConnectionEfficiencyConfig,
        SectionHints(
            {
                CONF_EFFICIENCY_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.EFFICIENCY,
                    time_series=True,
                    min_value=0.0,
                    max_value=1000.0,
                ),
                CONF_DRAWS_FROM_TARGET: FieldHint(
                    output_type=OutputType.STATUS,
                    default_mode="value",
                    default_value=False,
                ),
            }
        ),
    ]
    level: NotRequired[
        Annotated[
            LevelConfig,
            SectionHints(
                {
                    CONF_CONDUCTANCE: FieldHint(output_type=OutputType.CONDUCTANCE, time_series=True),
                    CONF_MAX_CONDUCTANCE: FieldHint(output_type=OutputType.CONDUCTANCE, time_series=True),
                }
            ),
        ]
    ]


class ConnectionConfigData(CommonData):
    """Connection element configuration with loaded values."""

    element_type: Literal[ElementType.CONNECTION]
    endpoints: EndpointsData
    power_limits: PowerLimitsData
    pricing: PricingData
    efficiency: ConnectionEfficiencyData
    level: NotRequired[LevelData]


__all__ = [
    "CONF_CONDUCTANCE",
    "CONF_DRAWS_FROM_TARGET",
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_MAX_CONDUCTANCE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_SOURCE",
    "CONF_TARGET",
    "ELEMENT_TYPE",
    "SECTION_EFFICIENCY",
    "SECTION_ENDPOINTS",
    "SECTION_LEVEL",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
    "ConnectionEfficiencyConfig",
    "ConnectionEfficiencyData",
    "EndpointsConfig",
    "EndpointsData",
    "LevelConfig",
    "LevelData",
]
