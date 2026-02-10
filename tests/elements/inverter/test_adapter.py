"""Tests for inverter adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import inverter
from custom_components.haeo.elements.availability import schema_config_available
from custom_components.haeo.schema import as_connection_target, as_entity_value


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Inverter available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        inverter.SECTION_COMMON: {
            "name": "test_inverter",
            "connection": as_connection_target("ac_bus"),
        },
        inverter.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.max_dc_to_ac"]),
            "max_power_target_source": as_entity_value(["sensor.max_ac_to_dc"]),
        },
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_first_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_dc_to_ac sensor is missing."""
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")
    # max_power_dc_to_ac is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        inverter.SECTION_COMMON: {
            "name": "test_inverter",
            "connection": as_connection_target("ac_bus"),
        },
        inverter.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.missing"]),
            "max_power_target_source": as_entity_value(["sensor.max_ac_to_dc"]),
        },
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_second_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_ac_to_dc sensor is missing."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    # max_power_ac_to_dc sensor is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        inverter.SECTION_COMMON: {
            "name": "test_inverter",
            "connection": as_connection_target("ac_bus"),
        },
        inverter.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.max_dc_to_ac"]),
            "max_power_target_source": as_entity_value(["sensor.missing"]),
        },
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, hass=hass)
    assert result is False


async def test_available_returns_true_when_limits_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return True when limits are omitted."""
    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        inverter.SECTION_COMMON: {
            "name": "test_inverter",
            "connection": as_connection_target("ac_bus"),
        },
        inverter.SECTION_POWER_LIMITS: {},
        inverter.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, hass=hass)
    assert result is True
