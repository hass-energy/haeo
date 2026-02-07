"""Grid element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.sections import (
    CONF_DEMAND_BLOCK_HOURS,
    CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET,
    CONF_DEMAND_PRICE_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_DEMAND_PRICING,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    ConnectedCommonConfig,
    ConnectedCommonData,
    PowerLimitsConfig,
    PowerLimitsData,
)

ELEMENT_TYPE: Final = "grid"
OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_DEMAND_PRICE_SOURCE_TARGET,
        CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET,
        CONF_DEMAND_BLOCK_HOURS,
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


class GridDemandPricingConfig(TypedDict, total=False):
    """Demand pricing configuration for grid imports."""

    demand_price_source_target: EntityValue | ConstantValue | NoneValue
    demand_current_energy_source_target: EntityValue | ConstantValue | NoneValue
    demand_block_hours: EntityValue | ConstantValue | NoneValue


class GridDemandPricingData(TypedDict, total=False):
    """Loaded demand pricing values for grid imports."""

    demand_price_source_target: NDArray[np.floating[Any]] | float
    demand_current_energy_source_target: NDArray[np.floating[Any]] | float
    demand_block_hours: float


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant."""

    element_type: Literal["grid"]
    common: ConnectedCommonConfig
    pricing: GridPricingConfig
    demand_pricing: GridDemandPricingConfig
    power_limits: PowerLimitsConfig


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values."""

    element_type: Literal["grid"]
    common: ConnectedCommonData
    pricing: GridPricingData
    demand_pricing: GridDemandPricingData
    power_limits: PowerLimitsData


__all__ = [
    "CONF_DEMAND_BLOCK_HOURS",
    "CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET",
    "CONF_DEMAND_PRICE_SOURCE_TARGET",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_DEMAND_PRICING",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "GridConfigData",
    "GridConfigSchema",
    "GridDemandPricingConfig",
    "GridDemandPricingData",
]
