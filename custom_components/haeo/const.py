"""Constants for the Home Assistant Energy Optimization integration."""

from homeassistant.components.sensor.const import UNIT_CONVERTERS, SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
import pulp


def convert_to_base_unit(value: float, from_unit: str | None, device_class: SensorDeviceClass) -> float:
    """Convert *value* expressed in *from_unit* to the canonical base unit.

    Power   → Watt (W)
    Energy  → Watt-hour (Wh)
    Storage → Watt-hour (Wh)
    All other classes are returned unchanged.
    """
    base_units = {
        SensorDeviceClass.POWER: UnitOfPower.WATT,
        SensorDeviceClass.ENERGY: UnitOfEnergy.WATT_HOUR,
        SensorDeviceClass.ENERGY_STORAGE: UnitOfEnergy.WATT_HOUR,
    }

    if device_class in base_units:
        return UNIT_CONVERTERS.get(device_class).convert(value, from_unit, base_units[device_class])

    return value


# Integration domain
DOMAIN = "haeo"

# Configuration keys
CONF_NAME = "name"
CONF_SOURCE = "source"
CONF_TARGET = "target"
CONF_MIN_POWER = "min_power"
CONF_MAX_POWER = "max_power"
CONF_ELEMENT_TYPE = "type"
CONF_PARTICIPANTS = "participants"

# Component types
ELEMENT_TYPE_BATTERY = "battery"
ELEMENT_TYPE_CONNECTION = "connection"
ELEMENT_TYPE_GRID = "grid"
ELEMENT_TYPE_CONSTANT_LOAD = "constant_load"
ELEMENT_TYPE_FORECAST_LOAD = "forecast_load"
ELEMENT_TYPE_GENERATOR = "generator"
ELEMENT_TYPE_NET = "net"

ELEMENT_TYPES = [
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_CONSTANT_LOAD,
    ELEMENT_TYPE_FORECAST_LOAD,
    ELEMENT_TYPE_GENERATOR,
    ELEMENT_TYPE_NET,
]
# Translation key mapping for element types
ELEMENT_TYPE_TRANSLATION_KEYS = {
    ELEMENT_TYPE_BATTERY: "entity.device.battery",
    ELEMENT_TYPE_GRID: "entity.device.grid",
    ELEMENT_TYPE_CONSTANT_LOAD: "entity.device.constant_load",
    ELEMENT_TYPE_FORECAST_LOAD: "entity.device.forecast_load",
    ELEMENT_TYPE_GENERATOR: "entity.device.generator",
    ELEMENT_TYPE_NET: "entity.device.net",
    ELEMENT_TYPE_CONNECTION: "entity.device.connection",
}


# Battery configuration keys
CONF_CAPACITY = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE = "initial_charge_percentage"
CONF_MIN_CHARGE_PERCENTAGE = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE = "max_charge_percentage"
CONF_MAX_CHARGE_POWER = "max_charge_power"
CONF_MAX_DISCHARGE_POWER = "max_discharge_power"
CONF_EFFICIENCY = "efficiency"
CONF_CHARGE_COST = "charge_cost"
CONF_DISCHARGE_COST = "discharge_cost"

# Grid configuration keys
CONF_IMPORT_LIMIT = "import_limit"
CONF_EXPORT_LIMIT = "export_limit"
CONF_IMPORT_PRICE = "import_price"
CONF_EXPORT_PRICE = "export_price"
CONF_IMPORT_PRICE_FORECAST = "import_price_forecast"
CONF_EXPORT_PRICE_FORECAST = "export_price_forecast"

# Load configuration keys
CONF_LOAD_TYPE = "load_type"
CONF_POWER = "power"
CONF_ENERGY = "energy"
CONF_FORECAST = "forecast"

# Load types
LOAD_TYPE_FIXED = "fixed"
LOAD_TYPE_VARIABLE = "variable"
LOAD_TYPE_FORECAST = "forecast"

# Generator configuration keys
CONF_CURTAILMENT = "curtailment"
CONF_PRICE_PRODUCTION = "price_production"
CONF_PRICE_CONSUMPTION = "price_consumption"
CONF_POWER = "power"

# Sensor configuration keys
CONF_SENSORS = "sensors"
CONF_SENSOR_ENTITY_ID = "entity_id"
CONF_SENSOR_ATTRIBUTE = "attribute"

# Dynamically determine available optimizers
AVAILABLE_OPTIMIZERS = pulp.listSolvers(onlyAvailable=True)

# Horizon and period configuration
CONF_HORIZON_HOURS = "horizon_hours"
CONF_PERIOD_MINUTES = "period_minutes"
CONF_OPTIMIZER = "optimizer"
DEFAULT_HORIZON_HOURS = 48  # 48 hours default
DEFAULT_PERIOD_MINUTES = 5  # 5 minutes default
DEFAULT_OPTIMIZER = "HiGHS"  # Default HiGHS solver

# Validation constants
MAX_HORIZON_HOURS = 168  # 1 week maximum
MAX_PERIOD_MINUTES = 60  # 1 hour maximum
MAX_NAME_LENGTH = 255

# Update intervals
DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes in seconds

# Optimization statuses
OPTIMIZATION_STATUS_SUCCESS = "success"
OPTIMIZATION_STATUS_FAILED = "failed"
OPTIMIZATION_STATUS_PENDING = "pending"


# Field property types
FIELD_TYPE_SENSOR = "sensor"
FIELD_TYPE_FORECAST = "forecast"
FIELD_TYPE_LIVE_FORECAST = "live_forecast"
FIELD_TYPE_CONSTANT = "constant"


# Entity attribute keys
ATTR_ENERGY = "energy"
ATTR_POWER = "power"
ATTR_FORECAST = "forecast"
