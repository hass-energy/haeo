"""Battery element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ElementTypeName = Literal["battery"]
ELEMENT_TYPE: ElementTypeName = "battery"

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

# Default values for optional fields
DEFAULTS: Final[dict[str, float]] = {
    CONF_MIN_CHARGE_PERCENTAGE: 0.0,
    CONF_MAX_CHARGE_PERCENTAGE: 100.0,
    CONF_EFFICIENCY: 99.0,
    CONF_EARLY_CHARGE_INCENTIVE: 0.001,
}


class BatteryConfigSchema(TypedDict):
    """Battery element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for sensors or constant values.
    """

    element_type: Literal["battery"]
    name: str
    connection: str  # Element name that battery connects to

    # Required sensors - can be entity links or constants
    capacity: list[str] | float  # Energy sensor entity IDs or constant value (kWh)
    initial_charge_percentage: list[str] | float  # SOC sensor entity IDs or constant value (%)

    # Optional fields - can be entity links, constants, or missing (uses default)
    min_charge_percentage: NotRequired[list[str] | float]
    max_charge_percentage: NotRequired[list[str] | float]
    efficiency: NotRequired[list[str] | float]

    # Optional power limits - can be entity links or constants
    max_charge_power: NotRequired[list[str] | float]  # Power sensor entity IDs or constant value (kW)
    max_discharge_power: NotRequired[list[str] | float]  # Power sensor entity IDs or constant value (kW)

    # Optional price fields - can be entity links or constants
    early_charge_incentive: NotRequired[list[str] | float]
    discharge_cost: NotRequired[list[str] | float]  # Price sensor entity IDs or constant value ($/kWh)

    # Advanced: undercharge/overcharge regions - can be entity links or constants
    undercharge_percentage: NotRequired[list[str] | float]
    overcharge_percentage: NotRequired[list[str] | float]
    undercharge_cost: NotRequired[list[str] | float]  # Price sensor entity IDs or constant value ($/kWh)
    overcharge_cost: NotRequired[list[str] | float]  # Price sensor entity IDs or constant value ($/kWh)


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

    # Time series with defaults applied
    min_charge_percentage: list[float]  # % per period
    max_charge_percentage: list[float]  # % per period
    efficiency: list[float]  # % per period

    # Optional loaded values
    max_charge_power: NotRequired[list[float]]  # kW per period
    max_discharge_power: NotRequired[list[float]]  # kW per period

    # Optional prices (time series)
    early_charge_incentive: NotRequired[list[float]]  # $/kWh per period
    discharge_cost: NotRequired[list[float]]  # $/kWh per period

    # Advanced: undercharge/overcharge regions (time series)
    undercharge_percentage: NotRequired[list[float]]  # % per period
    overcharge_percentage: NotRequired[list[float]]  # % per period
    undercharge_cost: NotRequired[list[float]]  # $/kWh per period
    overcharge_cost: NotRequired[list[float]]  # $/kWh per period
