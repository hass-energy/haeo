"""Battery element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.sections import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
    ConnectedCommonConfig,
    ConnectedCommonData,
    EfficiencyConfig,
    EfficiencyData,
    PowerLimitsConfig,
    PowerLimitsData,
    PricingConfig,
    PricingData,
    StorageSocConfig,
    StorageSocData,
)

ELEMENT_TYPE: Final = "battery"

SECTION_UNDERCHARGE: Final = "undercharge"
SECTION_OVERCHARGE: Final = "overcharge"
SECTION_LIMITS: Final = "limits"
SECTION_PARTITIONING: Final = "partitioning"

CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"
CONF_EFFICIENCY: Final = "efficiency"
CONF_CONFIGURE_PARTITIONS: Final = "configure_partitions"

CONF_PARTITION_PERCENTAGE: Final = "percentage"
CONF_PARTITION_COST: Final = "cost"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MIN_CHARGE_PERCENTAGE,
        CONF_MAX_CHARGE_PERCENTAGE,
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_EFFICIENCY,
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
        CONF_PARTITION_PERCENTAGE,
        CONF_PARTITION_COST,
    }
)

# Partition field names (hidden behind checkbox)
PARTITION_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    (
        CONF_PARTITION_PERCENTAGE,
        CONF_PARTITION_COST,
    )
)


type LimitsValueConfig = str | float
type LimitsValueData = NDArray[np.floating[Any]] | float


class LimitsConfig(TypedDict, total=False):
    """Charge percentage limits configuration."""

    min_charge_percentage: LimitsValueConfig
    max_charge_percentage: LimitsValueConfig


class LimitsData(TypedDict, total=False):
    """Loaded charge percentage limits."""

    min_charge_percentage: LimitsValueData
    max_charge_percentage: LimitsValueData


class PartitioningConfig(TypedDict, total=False):
    """Partitioning configuration values."""

    configure_partitions: bool


class PartitioningData(TypedDict, total=False):
    """Loaded partitioning values."""

    configure_partitions: bool


type PartitionPercentageConfig = str | float
type PartitionCostConfig = list[str] | str | float


class PartitionConfig(TypedDict, total=False):
    """Partition configuration (undercharge/overcharge)."""

    percentage: PartitionPercentageConfig
    cost: PartitionCostConfig


class PartitionData(TypedDict, total=False):
    """Loaded partition values (undercharge/overcharge)."""

    percentage: NDArray[np.floating[Any]] | float
    cost: NDArray[np.floating[Any]] | float


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant."""

    element_type: Literal["battery"]
    common: ConnectedCommonConfig
    storage: StorageSocConfig
    limits: LimitsConfig
    power_limits: PowerLimitsConfig
    pricing: PricingConfig
    efficiency: EfficiencyConfig
    partitioning: PartitioningConfig
    undercharge: NotRequired[PartitionConfig]
    overcharge: NotRequired[PartitionConfig]


class BatteryConfigData(TypedDict):
    """Battery element configuration with loaded values."""

    element_type: Literal["battery"]
    common: ConnectedCommonData
    storage: StorageSocData
    limits: LimitsData
    power_limits: PowerLimitsData
    pricing: PricingData
    efficiency: EfficiencyData
    partitioning: PartitioningData
    undercharge: NotRequired[PartitionData]
    overcharge: NotRequired[PartitionData]


__all__ = [
    "CONF_CAPACITY",
    "CONF_CONFIGURE_PARTITIONS",
    "CONF_CONNECTION",
    "CONF_EFFICIENCY",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "CONF_MAX_CHARGE_PERCENTAGE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_MIN_CHARGE_PERCENTAGE",
    "CONF_PARTITION_COST",
    "CONF_PARTITION_PERCENTAGE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "PARTITION_FIELD_NAMES",
    "SECTION_COMMON",
    "SECTION_EFFICIENCY",
    "SECTION_LIMITS",
    "SECTION_OVERCHARGE",
    "SECTION_PARTITIONING",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "SECTION_STORAGE",
    "SECTION_UNDERCHARGE",
    "BatteryConfigData",
    "BatteryConfigSchema",
]
