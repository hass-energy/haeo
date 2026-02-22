"""Battery element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.field_hints import FieldHint
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

ELEMENT_TYPE = ElementType.BATTERY

SECTION_STORAGE: Final = "storage"
SECTION_UNDERCHARGE: Final = "undercharge"
SECTION_OVERCHARGE: Final = "overcharge"
SECTION_LIMITS: Final = "limits"
SECTION_PARTITIONING: Final = "partitioning"

CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"

CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"
CONF_CONFIGURE_PARTITIONS: Final = "configure_partitions"

CONF_PARTITION_PERCENTAGE: Final = "percentage"
CONF_PARTITION_COST: Final = "cost"
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


FIELD_HINTS: Final[dict[str, dict[str, FieldHint]]] = {
    SECTION_STORAGE: {
        CONF_CAPACITY: FieldHint(
            output_type=OutputType.ENERGY,
            time_series=True,
            boundaries=True,
        ),
        CONF_INITIAL_CHARGE_PERCENTAGE: FieldHint(
            output_type=OutputType.STATE_OF_CHARGE,
            time_series=False,
            step=0.1,
        ),
    },
    SECTION_POWER_LIMITS: {
        CONF_MAX_POWER_TARGET_SOURCE: FieldHint(
            output_type=OutputType.POWER,
            direction="+",
            time_series=True,
            step=0.1,
            default_mode="entity",
        ),
        CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
            output_type=OutputType.POWER,
            direction="-",
            time_series=True,
            step=0.1,
            default_mode="entity",
        ),
    },
    SECTION_LIMITS: {
        CONF_MIN_CHARGE_PERCENTAGE: FieldHint(
            output_type=OutputType.STATE_OF_CHARGE,
            time_series=True,
            boundaries=True,
            default_value=0.0,
        ),
        CONF_MAX_CHARGE_PERCENTAGE: FieldHint(
            output_type=OutputType.STATE_OF_CHARGE,
            time_series=True,
            boundaries=True,
            default_value=100.0,
        ),
    },
    SECTION_EFFICIENCY: {
        CONF_EFFICIENCY_SOURCE_TARGET: FieldHint(
            output_type=OutputType.EFFICIENCY,
            time_series=True,
            default_mode="value",
            default_value=95.0,
        ),
        CONF_EFFICIENCY_TARGET_SOURCE: FieldHint(
            output_type=OutputType.EFFICIENCY,
            time_series=True,
            default_mode="value",
            default_value=95.0,
        ),
    },
    SECTION_PRICING: {
        CONF_PRICE_SOURCE_TARGET: FieldHint(
            output_type=OutputType.PRICE,
            direction="-",
            time_series=True,
            default_value=0.0,
        ),
        CONF_PRICE_TARGET_SOURCE: FieldHint(
            output_type=OutputType.PRICE,
            direction="-",
            time_series=True,
            default_value=0.0,
        ),
        CONF_SALVAGE_VALUE: FieldHint(
            output_type=OutputType.PRICE,
            time_series=False,
            default_value=0.0,
        ),
    },
    SECTION_UNDERCHARGE: {
        CONF_PARTITION_PERCENTAGE: FieldHint(
            output_type=OutputType.STATE_OF_CHARGE,
            time_series=True,
            boundaries=True,
            default_mode="value",
            default_value=0,
            force_required=True,
            device_type="undercharge_partition",
        ),
        CONF_PARTITION_COST: FieldHint(
            output_type=OutputType.PRICE,
            direction="-",
            time_series=True,
            default_mode="value",
            default_value=0,
            force_required=True,
            device_type="undercharge_partition",
        ),
    },
    SECTION_OVERCHARGE: {
        CONF_PARTITION_PERCENTAGE: FieldHint(
            output_type=OutputType.STATE_OF_CHARGE,
            time_series=True,
            boundaries=True,
            default_mode="value",
            default_value=100,
            force_required=True,
            device_type="overcharge_partition",
        ),
        CONF_PARTITION_COST: FieldHint(
            output_type=OutputType.PRICE,
            direction="-",
            time_series=True,
            default_mode="value",
            default_value=0,
            force_required=True,
            device_type="overcharge_partition",
        ),
    },
}


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


class PartitionConfig(TypedDict, total=False):
    """Partition configuration (undercharge/overcharge)."""

    percentage: EntityValue | ConstantValue | NoneValue
    cost: EntityValue | ConstantValue | NoneValue


class PartitionData(TypedDict, total=False):
    """Loaded partition values (undercharge/overcharge)."""

    percentage: NDArray[np.floating[Any]] | float
    cost: NDArray[np.floating[Any]] | float


class BatteryPricingConfig(PricingConfig):
    """Battery pricing configuration values."""

    salvage_value: EntityValue | ConstantValue | NoneValue


class BatteryPricingData(PricingData):
    """Loaded battery pricing values."""

    salvage_value: float


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.BATTERY]
    common: ConnectedCommonConfig
    storage: StorageSocConfig
    limits: LimitsConfig
    power_limits: PowerLimitsConfig
    pricing: BatteryPricingConfig
    efficiency: EfficiencyConfig
    partitioning: PartitioningConfig
    undercharge: NotRequired[PartitionConfig]
    overcharge: NotRequired[PartitionConfig]


class BatteryConfigData(TypedDict):
    """Battery element configuration with loaded values."""

    element_type: Literal[ElementType.BATTERY]
    common: ConnectedCommonData
    storage: StorageSocData
    limits: LimitsData
    power_limits: PowerLimitsData
    pricing: BatteryPricingData
    efficiency: EfficiencyData
    partitioning: PartitioningData
    undercharge: NotRequired[PartitionData]
    overcharge: NotRequired[PartitionData]


__all__ = [
    "CONF_CAPACITY",
    "CONF_CONFIGURE_PARTITIONS",
    "CONF_CONNECTION",
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "CONF_MAX_CHARGE_PERCENTAGE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_MIN_CHARGE_PERCENTAGE",
    "CONF_PARTITION_COST",
    "CONF_PARTITION_PERCENTAGE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_SALVAGE_VALUE",
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
    "BatteryPricingConfig",
    "BatteryPricingData",
    "LimitsConfig",
    "LimitsData",
    "PartitionConfig",
    "PartitionData",
    "PartitioningConfig",
    "PartitioningData",
    "StorageSocConfig",
    "StorageSocData",
]
