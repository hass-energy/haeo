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

# Partition field names (hidden behind checkbox)
PARTITION_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    (
        CONF_UNDERCHARGE_PERCENTAGE,
        CONF_OVERCHARGE_PERCENTAGE,
        CONF_UNDERCHARGE_COST,
        CONF_OVERCHARGE_COST,
    )
)


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for sensors or constant values.
    """

    element_type: Literal["battery"]
    name: str
    connection: str  # Element name that battery connects to

    # Required sensors - can be entity links or constants
    capacity: str | float  # Energy sensor entity ID or constant value (kWh)
    initial_charge_percentage: str | float  # SOC sensor entity ID or constant value (%)

    # Optional fields - can be entity links, constants, or missing (uses default)
    min_charge_percentage: NotRequired[str | float]
    max_charge_percentage: NotRequired[str | float]
    efficiency: NotRequired[str | float]

    # Optional power limits - can be entity links or constants
    max_charge_power: NotRequired[str | float]  # Power sensor entity ID or constant value (kW)
    max_discharge_power: NotRequired[str | float]  # Power sensor entity ID or constant value (kW)

    # Optional price fields - can be entity links or constants
    early_charge_incentive: NotRequired[str | float]
    discharge_cost: NotRequired[list[str] | str | float]  # Price sensors ($/kWh) - list for chaining

    # Partition configuration checkbox
    configure_partitions: NotRequired[bool]  # Whether to configure partition fields

    # Partition fields (only present when configure_partitions is True)
    undercharge_percentage: NotRequired[str | float]
    overcharge_percentage: NotRequired[str | float]
    undercharge_cost: NotRequired[list[str] | str | float]  # Price sensors ($/kWh) - list for chaining
    overcharge_cost: NotRequired[list[str] | str | float]  # Price sensors ($/kWh) - list for chaining


class BatteryConfigData(TypedDict):
    """Battery element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["battery"]
    name: str
    connection: str  # Element name that battery connects to

    # Loaded sensor values (time series)
    capacity: NDArray[np.floating[Any]]  # kWh per period
    initial_charge_percentage: NDArray[np.floating[Any]]  # Ratio per period (0-1, uses first value)

    # Time series with defaults applied in model_elements
    min_charge_percentage: NotRequired[NDArray[np.floating[Any]] | float]  # Ratio per period (0-1)
    max_charge_percentage: NotRequired[NDArray[np.floating[Any]] | float]  # Ratio per period (0-1)
    efficiency: NotRequired[NDArray[np.floating[Any]]]  # Ratio per period (0-1)

    # Optional loaded values
    max_charge_power: NotRequired[NDArray[np.floating[Any]]]  # kW per period
    max_discharge_power: NotRequired[NDArray[np.floating[Any]]]  # kW per period

    # Optional prices (time series)
    early_charge_incentive: NotRequired[NDArray[np.floating[Any]]]  # $/kWh per period
    discharge_cost: NotRequired[NDArray[np.floating[Any]]]  # $/kWh per period

    # Advanced: undercharge/overcharge regions (time series)
    undercharge_percentage: NotRequired[NDArray[np.floating[Any]] | float]  # Ratio per period (0-1)
    overcharge_percentage: NotRequired[NDArray[np.floating[Any]] | float]  # Ratio per period (0-1)
    undercharge_cost: NotRequired[NDArray[np.floating[Any]]]  # $/kWh per period
    overcharge_cost: NotRequired[NDArray[np.floating[Any]]]  # $/kWh per period
