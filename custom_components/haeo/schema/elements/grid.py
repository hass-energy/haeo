"""Grid element schema definitions."""

from typing import Annotated, Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.sections import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    ConnectedCommonConfig,
    ConnectedCommonData,
    PowerLimitsConfig,
    PowerLimitsData,
)

ELEMENT_TYPE = ElementType.GRID

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
    }
)


class GridPricingConfig(TypedDict):
    """Directional pricing configuration with required values."""

    price_source_target: EntityValue | ConstantValue | NoneValue
    price_target_source: EntityValue | ConstantValue | NoneValue


class GridPricingData(TypedDict):
    """Loaded directional pricing values with required entries."""

    price_source_target: NDArray[np.floating[Any]] | float
    price_target_source: NDArray[np.floating[Any]] | float


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.GRID]
    common: ConnectedCommonConfig
    pricing: Annotated[
        GridPricingConfig,
        SectionHints(
            {
                CONF_PRICE_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.PRICE,
                    direction="-",
                    time_series=True,
                ),
                CONF_PRICE_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.PRICE,
                    direction="+",
                    time_series=True,
                ),
            }
        ),
    ]
    power_limits: Annotated[
        PowerLimitsConfig,
        SectionHints(
            {
                CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    direction="+",
                    time_series=True,
                    default_mode="value",
                    default_value=100.0,
                ),
                CONF_MAX_POWER_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    direction="-",
                    time_series=True,
                    default_mode="value",
                    default_value=100.0,
                ),
            }
        ),
    ]


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values."""

    element_type: Literal[ElementType.GRID]
    common: ConnectedCommonData
    pricing: GridPricingData
    power_limits: PowerLimitsData


__all__ = [
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "GridConfigData",
    "GridConfigSchema",
    "GridPricingConfig",
    "GridPricingData",
]
