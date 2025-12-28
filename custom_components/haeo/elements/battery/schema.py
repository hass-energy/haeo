"""Battery element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

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

# Default values
DEFAULT_MIN_CHARGE_PERCENTAGE: Final = 0.0
DEFAULT_MAX_CHARGE_PERCENTAGE: Final = 100.0
DEFAULT_EFFICIENCY: Final = 99.0
DEFAULT_EARLY_CHARGE_INCENTIVE: Final = 0.001


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for sensors.
    """

    element_type: Literal["battery"]
    name: str
    connection: str  # Element name that battery connects to

    # Required sensors
    capacity: list[str]  # Energy sensor entity IDs
    initial_charge_percentage: list[str]  # SOC sensor entity IDs

    # Optional percentages with defaults
    min_charge_percentage: NotRequired[float]  # Default 0%
    max_charge_percentage: NotRequired[float]  # Default 100%
    efficiency: NotRequired[float]  # Default 99%

    # Optional sensor fields
    max_charge_power: NotRequired[list[str]]  # Power sensor entity IDs
    max_discharge_power: NotRequired[list[str]]  # Power sensor entity IDs

    # Optional price fields
    early_charge_incentive: NotRequired[float]  # Default 0.001
    discharge_cost: NotRequired[list[str]]  # Price sensor entity IDs

    # Advanced: undercharge/overcharge regions
    undercharge_percentage: NotRequired[float]
    overcharge_percentage: NotRequired[float]
    undercharge_cost: NotRequired[list[str]]  # Price sensor entity IDs
    overcharge_cost: NotRequired[list[str]]  # Price sensor entity IDs


class BatteryConfigData(TypedDict):
    """Battery element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["battery"]
    name: str
    connection: str  # Element name that battery connects to

    # Loaded sensor values (time series)
    capacity: list[float]  # kWh per period
    initial_charge_percentage: list[float]  # % per period (uses first value)

    # Scalars with defaults applied
    min_charge_percentage: float
    max_charge_percentage: float
    efficiency: float

    # Optional loaded values
    max_charge_power: NotRequired[list[float]]  # kW per period
    max_discharge_power: NotRequired[list[float]]  # kW per period

    # Optional prices
    early_charge_incentive: NotRequired[float]  # $/kWh
    discharge_cost: NotRequired[list[float]]  # $/kWh per period

    # Advanced: undercharge/overcharge regions
    undercharge_percentage: NotRequired[float]  # %
    overcharge_percentage: NotRequired[float]  # %
    undercharge_cost: NotRequired[list[float]]  # $/kWh per period
    overcharge_cost: NotRequired[list[float]]  # $/kWh per period
