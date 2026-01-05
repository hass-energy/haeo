"""Battery element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType

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
INPUT_FIELDS: Final[tuple[InputFieldInfo[NumberEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_CAPACITY,
        entity_description=NumberEntityDescription(
            key=CONF_CAPACITY,
            translation_key=f"{ELEMENT_TYPE}_{CONF_CAPACITY}",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=NumberDeviceClass.ENERGY_STORAGE,
            native_min_value=0.1,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.ENERGY,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_INITIAL_CHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_INITIAL_CHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_INITIAL_CHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_MIN_CHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_MIN_CHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MIN_CHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
        default=0.0,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_CHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_CHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_CHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
        default=100.0,
    ),
    InputFieldInfo(
        field_name=CONF_EFFICIENCY,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.EFFICIENCY,
        time_series=True,
        default=99.0,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_CHARGE_POWER,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_CHARGE_POWER,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_CHARGE_POWER}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER,
        direction="+",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_DISCHARGE_POWER,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_DISCHARGE_POWER,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_DISCHARGE_POWER}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER,
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_EARLY_CHARGE_INCENTIVE,
        entity_description=NumberEntityDescription(
            key=CONF_EARLY_CHARGE_INCENTIVE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EARLY_CHARGE_INCENTIVE}",
            native_min_value=0.0,
            native_max_value=1.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
        default=0.001,
    ),
    InputFieldInfo(
        field_name=CONF_DISCHARGE_COST,
        entity_description=NumberEntityDescription(
            key=CONF_DISCHARGE_COST,
            translation_key=f"{ELEMENT_TYPE}_{CONF_DISCHARGE_COST}",
            native_min_value=0.0,
            native_max_value=1.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_UNDERCHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_UNDERCHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_UNDERCHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_OVERCHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_OVERCHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_OVERCHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_UNDERCHARGE_COST,
        entity_description=NumberEntityDescription(
            key=CONF_UNDERCHARGE_COST,
            translation_key=f"{ELEMENT_TYPE}_{CONF_UNDERCHARGE_COST}",
            native_min_value=0.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_OVERCHARGE_COST,
        entity_description=NumberEntityDescription(
            key=CONF_OVERCHARGE_COST,
            translation_key=f"{ELEMENT_TYPE}_{CONF_OVERCHARGE_COST}",
            native_min_value=0.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
    ),
)


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
