"""Constants for the Home Assistant Energy Optimization integration."""

from typing import Final

from homeassistant.components.sensor.const import UNIT_CONVERTERS, SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower


def convert_to_base_unit(value: float, from_unit: str | None, device_class: SensorDeviceClass | None) -> float:
    """Convert *value* expressed in *from_unit* to the canonical base unit.

    Power   → Kilowatt (kW)
    Energy  → Kilowatt-hour (kWh)
    Storage → Kilowatt-hour (kWh)
    All other classes are returned unchanged.
    """
    base_units: Final = {
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
DOMAIN: Final = "haeo"

# Integration types
INTEGRATION_TYPE_HUB: Final = "hub"

# Configuration keys
CONF_NAME: Final = "name"
CONF_INTEGRATION_TYPE: Final = "integration_type"
CONF_ELEMENT_TYPE: Final = "element_type"
CONF_UPDATE_INTERVAL_MINUTES: Final = "update_interval_minutes"
CONF_DEBOUNCE_SECONDS: Final = "debounce_seconds"

ELEMENT_TYPE_NETWORK: Final = "network"

# Horizon and period configuration
CONF_HORIZON_HOURS: Final = "horizon_hours"
CONF_PERIOD_MINUTES: Final = "period_minutes"
DEFAULT_HORIZON_HOURS: Final = 48  # 48 hours default
DEFAULT_PERIOD_MINUTES: Final = 5  # 5 minutes default
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 5  # 5 minutes default
DEFAULT_DEBOUNCE_SECONDS: Final = 2  # 2 seconds debounce window

# Optimization statuses
OPTIMIZATION_STATUS_SUCCESS: Final = "success"
OPTIMIZATION_STATUS_FAILED: Final = "failed"
OPTIMIZATION_STATUS_PENDING: Final = "pending"
