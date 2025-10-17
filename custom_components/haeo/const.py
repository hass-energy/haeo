"""Constants for the Home Assistant Energy Optimization integration."""

from homeassistant.components.sensor.const import UNIT_CONVERTERS, SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
import pulp


def convert_to_base_unit(value: float, from_unit: str | None, device_class: SensorDeviceClass | None) -> float:
    """Convert *value* expressed in *from_unit* to the canonical base unit.

    Power   → Kilowatt (kW)
    Energy  → Kilowatt-hour (kWh)
    Storage → Kilowatt-hour (kWh)
    All other classes are returned unchanged.
    """
    base_units = {
        SensorDeviceClass.POWER: UnitOfPower.KILO_WATT,
        SensorDeviceClass.ENERGY: UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY_STORAGE: UnitOfEnergy.KILO_WATT_HOUR,
    }

    if device_class in base_units:
        converter = UNIT_CONVERTERS.get(device_class)
        if converter is not None:
            return converter.convert(value, from_unit, base_units[device_class])

    return value


# Integration domain
DOMAIN = "haeo"

# Integration types
INTEGRATION_TYPE_HUB = "hub"

# Configuration keys
CONF_NAME = "name"
CONF_INTEGRATION_TYPE = "integration_type"
CONF_SOURCE = "source"
CONF_TARGET = "target"
CONF_MIN_POWER = "min_power"
CONF_MAX_POWER = "max_power"
CONF_ELEMENT_TYPE = "type"
CONF_PARTICIPANTS = "participants"
CONF_PARENT_ENTRY_ID = "parent_entry_id"

# Component types
ELEMENT_TYPE_BATTERY = "battery"
ELEMENT_TYPE_CONNECTION = "connection"
ELEMENT_TYPE_GRID = "grid"
ELEMENT_TYPE_CONSTANT_LOAD = "constant_load"
ELEMENT_TYPE_FORECAST_LOAD = "forecast_load"
ELEMENT_TYPE_PHOTOVOLTAICS = "photovoltaics"
ELEMENT_TYPE_NODE = "node"
ELEMENT_TYPE_NETWORK = "network"

ELEMENT_TYPES = [
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_CONSTANT_LOAD,
    ELEMENT_TYPE_FORECAST_LOAD,
    ELEMENT_TYPE_PHOTOVOLTAICS,
    ELEMENT_TYPE_NODE,
    ELEMENT_TYPE_NETWORK,
]

# Sensor types (translation keys for sensors)
SENSOR_TYPE_OPTIMIZATION_COST = "optimization_cost"
SENSOR_TYPE_OPTIMIZATION_STATUS = "optimization_status"
SENSOR_TYPE_OPTIMIZATION_DURATION = "optimization_duration"
SENSOR_TYPE_POWER = "power"
SENSOR_TYPE_ENERGY = "energy"
SENSOR_TYPE_SOC = "soc"

SENSOR_TYPES = [
    SENSOR_TYPE_OPTIMIZATION_COST,
    SENSOR_TYPE_OPTIMIZATION_STATUS,
    SENSOR_TYPE_OPTIMIZATION_DURATION,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_ENERGY,
    SENSOR_TYPE_SOC,
]
# Translation key mapping for element types
ELEMENT_TYPE_TRANSLATION_KEYS = {
    ELEMENT_TYPE_BATTERY: "entity.device.battery",
    ELEMENT_TYPE_GRID: "entity.device.grid",
    ELEMENT_TYPE_CONSTANT_LOAD: "entity.device.constant_load",
    ELEMENT_TYPE_FORECAST_LOAD: "entity.device.forecast_load",
    ELEMENT_TYPE_PHOTOVOLTAICS: "entity.device.photovoltaics",
    ELEMENT_TYPE_NODE: "entity.device.node",
    ELEMENT_TYPE_NETWORK: "entity.device.network",
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

# Photovoltaics configuration keys
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
DEFAULT_OPTIMIZER = "highs"  # Default HiGHS solver (using lowercase key)

# Map translation-friendly optimizer keys (lowercase) to actual optimizer names
OPTIMIZER_NAME_MAP = {name.lower(): name for name in AVAILABLE_OPTIMIZERS}


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
