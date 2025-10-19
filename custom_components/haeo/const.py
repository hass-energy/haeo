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

    if device_class is None:
        return value

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
CONF_ELEMENT_TYPE = "type"
CONF_PARTICIPANTS = "participants"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
CONF_DEBOUNCE_SECONDS = "debounce_seconds"
CONF_PARENT_ENTRY_ID = "parent_entry_id"

ELEMENT_TYPE_NETWORK = "network"

# Dynamically determine available optimizers
AVAILABLE_OPTIMIZERS = pulp.listSolvers(onlyAvailable=True)

# Horizon and period configuration
CONF_HORIZON_HOURS = "horizon_hours"
CONF_PERIOD_MINUTES = "period_minutes"
CONF_OPTIMIZER = "optimizer"
DEFAULT_HORIZON_HOURS = 48  # 48 hours default
DEFAULT_PERIOD_MINUTES = 5  # 5 minutes default
DEFAULT_UPDATE_INTERVAL_MINUTES = 5  # 5 minutes default
DEFAULT_OPTIMIZER = "highs"  # Default HiGHS solver (using lowercase key)
DEFAULT_DEBOUNCE_SECONDS = 2  # 2 seconds debounce window

# Map translation-friendly optimizer keys (lowercase) to actual optimizer names
OPTIMIZER_NAME_MAP = {name.lower(): name for name in AVAILABLE_OPTIMIZERS}


# Validation constants
MAX_HORIZON_HOURS = 168  # 1 week maximum
MAX_PERIOD_MINUTES = 60  # 1 hour maximum
MAX_NAME_LENGTH = 255

# Update intervals
DEFAULT_UPDATE_INTERVAL = DEFAULT_UPDATE_INTERVAL_MINUTES * 60  # Convenience constant in seconds

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
