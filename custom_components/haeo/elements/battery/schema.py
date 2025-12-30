"""Battery element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower

from custom_components.haeo.elements.input_fields import InputEntityType, InputFieldInfo

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

# Default values for optional fields
DEFAULTS: Final[dict[str, float]] = {
    CONF_MIN_CHARGE_PERCENTAGE: 0.0,
    CONF_MAX_CHARGE_PERCENTAGE: 100.0,
    CONF_EFFICIENCY: 99.0,
    CONF_EARLY_CHARGE_INCENTIVE: 0.001,
}

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name=CONF_CAPACITY,
        entity_type=InputEntityType.NUMBER,
        output_type="energy",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        min_value=0.1,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.ENERGY_STORAGE,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_INITIAL_CHARGE_PERCENTAGE,
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.BATTERY,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_MIN_CHARGE_PERCENTAGE,
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_CHARGE_PERCENTAGE,
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name=CONF_EFFICIENCY,
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=50.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER_FACTOR,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_CHARGE_POWER,
        entity_type=InputEntityType.NUMBER,
        output_type="power",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        direction="+",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_DISCHARGE_POWER,
        entity_type=InputEntityType.NUMBER,
        output_type="power",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_EARLY_CHARGE_INCENTIVE,
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=0.0,
        max_value=1.0,
        step=0.001,
    ),
    InputFieldInfo(
        field_name=CONF_DISCHARGE_COST,
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=0.0,
        max_value=1.0,
        step=0.001,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_UNDERCHARGE_PERCENTAGE,
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name=CONF_OVERCHARGE_PERCENTAGE,
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name=CONF_UNDERCHARGE_COST,
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=0.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_OVERCHARGE_COST,
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=0.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
)


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
    min_charge_percentage: NotRequired[float]
    max_charge_percentage: NotRequired[float]
    efficiency: NotRequired[float]

    # Optional sensor fields
    max_charge_power: NotRequired[list[str]]  # Power sensor entity IDs
    max_discharge_power: NotRequired[list[str]]  # Power sensor entity IDs

    # Optional price fields
    early_charge_incentive: NotRequired[float]
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
