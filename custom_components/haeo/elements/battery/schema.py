"""Battery element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.sections import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
    BasicNameConnectionConfig,
    BasicNameConnectionData,
)

ELEMENT_TYPE: Final = "battery"

SECTION_UNDERCHARGE: Final = "undercharge"
SECTION_OVERCHARGE: Final = "overcharge"

CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"
CONF_MAX_CHARGE_POWER: Final = "max_charge_power"
CONF_MAX_DISCHARGE_POWER: Final = "max_discharge_power"

CONF_EFFICIENCY: Final = "efficiency"
CONF_CONFIGURE_PARTITIONS: Final = "configure_partitions"

CONF_EARLY_CHARGE_INCENTIVE: Final = "early_charge_incentive"
CONF_DISCHARGE_COST: Final = "discharge_cost"

CONF_PARTITION_PERCENTAGE: Final = "percentage"
CONF_PARTITION_COST: Final = "cost"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MIN_CHARGE_PERCENTAGE,
        CONF_MAX_CHARGE_PERCENTAGE,
        CONF_EFFICIENCY,
        CONF_MAX_CHARGE_POWER,
        CONF_MAX_DISCHARGE_POWER,
        CONF_EARLY_CHARGE_INCENTIVE,
        CONF_DISCHARGE_COST,
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


class BatteryStorageConfig(TypedDict):
    """Storage configuration for battery elements."""

    capacity: str | float
    initial_charge_percentage: str | float


class BatteryStorageData(TypedDict):
    """Loaded storage values for battery elements."""

    capacity: NDArray[np.floating[Any]] | float
    initial_charge_percentage: NDArray[np.floating[Any]] | float


class BatteryLimitsConfig(TypedDict, total=False):
    """Limit configuration for battery elements."""

    min_charge_percentage: str | float
    max_charge_percentage: str | float
    max_charge_power: str | float
    max_discharge_power: str | float


class BatteryLimitsData(TypedDict, total=False):
    """Loaded limit values for battery elements."""

    min_charge_percentage: NDArray[np.floating[Any]] | float
    max_charge_percentage: NDArray[np.floating[Any]] | float
    max_charge_power: NDArray[np.floating[Any]] | float
    max_discharge_power: NDArray[np.floating[Any]] | float


class BatteryPricingConfig(TypedDict, total=False):
    """Pricing configuration for battery elements."""

    early_charge_incentive: str | float
    discharge_cost: list[str] | str | float


class BatteryPricingData(TypedDict, total=False):
    """Loaded pricing values for battery elements."""

    early_charge_incentive: NDArray[np.floating[Any]] | float
    discharge_cost: NDArray[np.floating[Any]] | float


class BatteryAdvancedConfig(TypedDict, total=False):
    """Advanced configuration for battery elements."""

    efficiency: str | float
    configure_partitions: bool


class BatteryAdvancedData(TypedDict, total=False):
    """Loaded advanced values for battery elements."""

    efficiency: NDArray[np.floating[Any]] | float
    configure_partitions: bool


type PartitionPercentageConfig = str | float
type PartitionCostConfig = list[str] | str | float


class PartitionConfig(TypedDict, total=False):
    """Partition configuration (undercharge/overcharge)."""

    percentage: PartitionPercentageConfig
    cost: PartitionCostConfig


type PartitionValueData = NDArray[np.floating[Any]] | float


class PartitionData(TypedDict, total=False):
    """Loaded partition values (undercharge/overcharge)."""

    percentage: PartitionValueData
    cost: PartitionValueData


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant."""

    element_type: Literal["battery"]
    basic: BasicNameConnectionConfig
    storage: BatteryStorageConfig
    limits: BatteryLimitsConfig
    pricing: BatteryPricingConfig
    advanced: BatteryAdvancedConfig
    undercharge: NotRequired[PartitionConfig]
    overcharge: NotRequired[PartitionConfig]


class BatteryConfigData(TypedDict):
    """Battery element configuration with loaded values."""

    element_type: Literal["battery"]
    basic: BasicNameConnectionData
    storage: BatteryStorageData
    limits: BatteryLimitsData
    pricing: BatteryPricingData
    advanced: BatteryAdvancedData
    undercharge: NotRequired[PartitionData]
    overcharge: NotRequired[PartitionData]


__all__ = [
    "CONF_CAPACITY",
    "CONF_CONFIGURE_PARTITIONS",
    "CONF_CONNECTION",
    "CONF_DISCHARGE_COST",
    "CONF_EARLY_CHARGE_INCENTIVE",
    "CONF_EFFICIENCY",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "CONF_MAX_CHARGE_PERCENTAGE",
    "CONF_MAX_CHARGE_POWER",
    "CONF_MAX_DISCHARGE_POWER",
    "CONF_MIN_CHARGE_PERCENTAGE",
    "CONF_PARTITION_COST",
    "CONF_PARTITION_PERCENTAGE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "PARTITION_FIELD_NAMES",
    "SECTION_ADVANCED",
    "SECTION_BASIC",
    "SECTION_LIMITS",
    "SECTION_OVERCHARGE",
    "SECTION_PRICING",
    "SECTION_STORAGE",
    "SECTION_UNDERCHARGE",
    "BatteryConfigData",
    "BatteryConfigSchema",
]
