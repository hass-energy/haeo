"""Battery element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "battery"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"
CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"
CONF_EFFICIENCY: Final = "efficiency"
CONF_MAX_CHARGE_POWER: Final = "max_charge_power"
CONF_MAX_DISCHARGE_POWER: Final = "max_discharge_power"
CONF_EARLY_CHARGE_INCENTIVE: Final = "early_charge_incentive"
CONF_DISCHARGE_COST: Final = "discharge_cost"
CONF_UNDERCHARGE_PERCENTAGE: Final = "undercharge_percentage"
CONF_OVERCHARGE_PERCENTAGE: Final = "overcharge_percentage"
CONF_UNDERCHARGE_COST: Final = "undercharge_cost"
CONF_OVERCHARGE_COST: Final = "overcharge_cost"
CONF_CONNECTION: Final = "connection"
CONF_CONFIGURE_PARTITIONS: Final = "configure_partitions"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_LIMITS: Final = "limits"
CONF_SECTION_ADVANCED: Final = "advanced"
CONF_SECTION_UNDERCHARGE: Final = "undercharge"
CONF_SECTION_OVERCHARGE: Final = "overcharge"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MIN_CHARGE_PERCENTAGE,
        CONF_MAX_CHARGE_PERCENTAGE,
        CONF_EFFICIENCY,
        CONF_MAX_CHARGE_POWER,
        CONF_MAX_DISCHARGE_POWER,
        CONF_EARLY_CHARGE_INCENTIVE,
        CONF_DISCHARGE_COST,
        CONF_UNDERCHARGE_PERCENTAGE,
        CONF_UNDERCHARGE_COST,
        CONF_OVERCHARGE_PERCENTAGE,
        CONF_OVERCHARGE_COST,
    }
)

# Partition field names (hidden behind checkbox)
PARTITION_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    (
        CONF_UNDERCHARGE_PERCENTAGE,
        CONF_OVERCHARGE_PERCENTAGE,
        CONF_UNDERCHARGE_COST,
        CONF_OVERCHARGE_COST,
    )
)


class BatteryBasicConfig(TypedDict):
    """Basic configuration for battery elements."""

    name: str
    connection: str  # Element name that battery connects to
    capacity: str | float  # Energy sensor entity ID or constant value (kWh)
    initial_charge_percentage: str | float  # SOC sensor entity ID or constant value (%)


class BatteryLimitsConfig(TypedDict, total=False):
    """Limit configuration for battery elements."""

    min_charge_percentage: str | float
    max_charge_percentage: str | float
    max_charge_power: str | float  # Power sensor entity ID or constant value (kW)
    max_discharge_power: str | float  # Power sensor entity ID or constant value (kW)


class BatteryAdvancedConfig(TypedDict, total=False):
    """Advanced configuration for battery elements."""

    efficiency: str | float
    early_charge_incentive: str | float
    discharge_cost: list[str] | str | float  # Price sensors ($/kWh) - list for chaining
    configure_partitions: bool  # Whether to configure partition fields


type BatteryPartitionPercentageConfig = str | float
type BatteryPartitionCostConfig = list[str] | str | float


class BatteryPartitionUnderchargeConfig(TypedDict, total=False):
    """Undercharge partition configuration."""

    undercharge_percentage: BatteryPartitionPercentageConfig
    undercharge_cost: BatteryPartitionCostConfig  # Price sensors ($/kWh) - list for chaining


class BatteryPartitionOverchargeConfig(TypedDict, total=False):
    """Overcharge partition configuration."""

    overcharge_percentage: BatteryPartitionPercentageConfig
    overcharge_cost: BatteryPartitionCostConfig  # Price sensors ($/kWh) - list for chaining


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for sensors or constant values.
    """

    element_type: Literal["battery"]
    basic: BatteryBasicConfig
    limits: BatteryLimitsConfig
    advanced: BatteryAdvancedConfig
    undercharge: NotRequired[BatteryPartitionUnderchargeConfig]
    overcharge: NotRequired[BatteryPartitionOverchargeConfig]


class BatteryBasicData(TypedDict):
    """Loaded basic values for battery elements."""

    name: str
    connection: str  # Element name that battery connects to
    capacity: NDArray[np.floating[Any]]  # kWh per period
    initial_charge_percentage: NDArray[np.floating[Any]]  # Ratio per period (0-1, uses first value)


class BatteryLimitsData(TypedDict, total=False):
    """Loaded limit values for battery elements."""

    min_charge_percentage: NDArray[np.floating[Any]] | float  # Ratio per period (0-1)
    max_charge_percentage: NDArray[np.floating[Any]] | float  # Ratio per period (0-1)
    max_charge_power: NDArray[np.floating[Any]]  # kW per period
    max_discharge_power: NDArray[np.floating[Any]]  # kW per period


class BatteryAdvancedData(TypedDict, total=False):
    """Loaded advanced values for battery elements."""

    efficiency: NDArray[np.floating[Any]] | float  # Ratio per period (0-1)
    early_charge_incentive: NDArray[np.floating[Any]]  # $/kWh per period
    discharge_cost: NDArray[np.floating[Any]]  # $/kWh per period
    configure_partitions: bool


type BatteryPartitionValueData = NDArray[np.floating[Any]] | float


class BatteryPartitionUnderchargeData(TypedDict, total=False):
    """Loaded undercharge partition values."""

    undercharge_percentage: BatteryPartitionValueData  # Ratio per period (0-1)
    undercharge_cost: BatteryPartitionValueData  # $/kWh per period


class BatteryPartitionOverchargeData(TypedDict, total=False):
    """Loaded overcharge partition values."""

    overcharge_percentage: BatteryPartitionValueData  # Ratio per period (0-1)
    overcharge_cost: BatteryPartitionValueData  # $/kWh per period


class BatteryConfigData(TypedDict):
    """Battery element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["battery"]
    basic: BatteryBasicData
    limits: BatteryLimitsData
    advanced: BatteryAdvancedData
    undercharge: NotRequired[BatteryPartitionUnderchargeData]
    overcharge: NotRequired[BatteryPartitionOverchargeData]
