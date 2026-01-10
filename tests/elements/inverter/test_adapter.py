"""Tests for inverter adapter available() function."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import inverter


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Inverter available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": ["sensor.max_dc_to_ac"],
        "max_power_ac_to_dc": ["sensor.max_ac_to_dc"],
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_first_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_dc_to_ac sensor is missing."""
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")
    # max_power_dc_to_ac is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": ["sensor.missing"],
        "max_power_ac_to_dc": ["sensor.max_ac_to_dc"],
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_second_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_ac_to_dc sensor is missing."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    # max_power_ac_to_dc sensor is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": ["sensor.max_dc_to_ac"],
        "max_power_ac_to_dc": ["sensor.missing"],
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is False
