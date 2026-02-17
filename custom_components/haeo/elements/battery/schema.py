"""Battery element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.sections import (
    CONF_CONNECTION,
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
    ConnectedCommonConfig,
    ConnectedCommonData,
    EfficiencyConfig,
    EfficiencyData,
    PowerLimitsConfig,
    PowerLimitsData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE: Final = "battery"

SECTION_STORAGE: Final = "storage"
SECTION_LIMITS: Final = "limits"
SECTION_PARTITIONING: Final = "partitioning"
SECTION_PARTITIONS: Final = "partitions"

CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"

CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"
CONF_CONFIGURE_PARTITIONS: Final = "configure_partitions"

CONF_PARTITION_NAMES: Final = "partition_names"
CONF_THRESHOLD_KWH: Final = "threshold_kwh"
CONF_CHARGE_VIOLATION_PRICE: Final = "charge_violation_price"
CONF_DISCHARGE_VIOLATION_PRICE: Final = "discharge_violation_price"
CONF_CHARGE_PRICE: Final = "charge_price"
CONF_DISCHARGE_PRICE: Final = "discharge_price"
CONF_CHARGE_RECOVERY_REWARD: Final = "charge_recovery_reward"
CONF_DISCHARGE_RECOVERY_REWARD: Final = "discharge_recovery_reward"
CONF_SALVAGE_VALUE: Final = "salvage_value"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MIN_CHARGE_PERCENTAGE,
        CONF_MAX_CHARGE_PERCENTAGE,
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_EFFICIENCY_SOURCE_TARGET,
        CONF_EFFICIENCY_TARGET_SOURCE,
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
        CONF_SALVAGE_VALUE,
    }
)


class StorageSocConfig(TypedDict):
    """Storage config with required SOC percentage."""

    capacity: EntityValue | ConstantValue
    initial_charge_percentage: EntityValue | ConstantValue


class StorageSocData(TypedDict):
    """Loaded storage values with required SOC percentage."""

    capacity: NDArray[np.floating[Any]]
    initial_charge_percentage: float


class LimitsConfig(TypedDict, total=False):
    """Charge percentage limits configuration."""

    min_charge_percentage: EntityValue | ConstantValue | NoneValue
    max_charge_percentage: EntityValue | ConstantValue | NoneValue


class LimitsData(TypedDict, total=False):
    """Loaded charge percentage limits."""

    min_charge_percentage: NDArray[np.floating[Any]] | float
    max_charge_percentage: NDArray[np.floating[Any]] | float


class PartitioningConfig(TypedDict, total=False):
    """Partitioning configuration values."""

    configure_partitions: bool


class PartitioningData(TypedDict, total=False):
    """Loaded partitioning values."""

    configure_partitions: bool


class ZoneConfig(TypedDict):
    """SOC pricing zone configuration."""

    threshold_kwh: EntityValue | ConstantValue
    charge_violation_price: NotRequired[EntityValue | ConstantValue | NoneValue]
    discharge_violation_price: NotRequired[EntityValue | ConstantValue | NoneValue]
    charge_price: NotRequired[EntityValue | ConstantValue | NoneValue]
    discharge_price: NotRequired[EntityValue | ConstantValue | NoneValue]
    charge_recovery_reward: NotRequired[EntityValue | ConstantValue | NoneValue]
    discharge_recovery_reward: NotRequired[EntityValue | ConstantValue | NoneValue]


class ZoneData(TypedDict):
    """Loaded SOC pricing zone values."""

    threshold_kwh: NDArray[np.floating[Any]] | float
    charge_violation_price: NotRequired[NDArray[np.floating[Any]] | float]
    discharge_violation_price: NotRequired[NDArray[np.floating[Any]] | float]
    charge_price: NotRequired[NDArray[np.floating[Any]] | float]
    discharge_price: NotRequired[NDArray[np.floating[Any]] | float]
    charge_recovery_reward: NotRequired[NDArray[np.floating[Any]] | float]
    discharge_recovery_reward: NotRequired[NDArray[np.floating[Any]] | float]


class BatteryPricingConfig(PricingConfig):
    """Battery pricing configuration values."""

    salvage_value: EntityValue | ConstantValue | NoneValue


class BatteryPricingData(PricingData):
    """Loaded battery pricing values."""

    salvage_value: float


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant."""

    element_type: Literal["battery"]
    common: ConnectedCommonConfig
    storage: StorageSocConfig
    limits: LimitsConfig
    power_limits: PowerLimitsConfig
    pricing: BatteryPricingConfig
    efficiency: EfficiencyConfig
    partitioning: PartitioningConfig
    partitions: NotRequired[dict[str, ZoneConfig]]


class BatteryConfigData(TypedDict):
    """Battery element configuration with loaded values."""

    element_type: Literal["battery"]
    common: ConnectedCommonData
    storage: StorageSocData
    limits: LimitsData
    power_limits: PowerLimitsData
    pricing: BatteryPricingData
    efficiency: EfficiencyData
    partitioning: PartitioningData
    partitions: NotRequired[dict[str, ZoneData]]


__all__ = [
    "CONF_CAPACITY",
    "CONF_CONFIGURE_PARTITIONS",
    "CONF_CONNECTION",
    "CONF_CHARGE_RECOVERY_REWARD",
    "CONF_CHARGE_VIOLATION_PRICE",
    "CONF_DISCHARGE_PRICE",
    "CONF_DISCHARGE_RECOVERY_REWARD",
    "CONF_DISCHARGE_VIOLATION_PRICE",
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "CONF_CHARGE_PRICE",
    "CONF_MAX_CHARGE_PERCENTAGE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_MIN_CHARGE_PERCENTAGE",
    "CONF_PARTITION_NAMES",
    "CONF_SALVAGE_VALUE",
    "CONF_THRESHOLD_KWH",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_EFFICIENCY",
    "SECTION_LIMITS",
    "SECTION_PARTITIONING",
    "SECTION_PARTITIONS",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "SECTION_STORAGE",
    "BatteryConfigData",
    "BatteryConfigSchema",
    "BatteryPricingConfig",
    "BatteryPricingData",
    "ZoneConfig",
    "ZoneData",
]
