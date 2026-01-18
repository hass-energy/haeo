"""Tests for inverter adapter build_config_data() and available() functions."""

import numpy as np
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
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
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
        "max_power_dc_to_ac": "sensor.missing",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
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
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.missing",
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is False


def test_build_config_data_returns_config_data() -> None:
    """build_config_data() should return ConfigData with loaded values."""
    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
    }
    loaded_values = {
        "max_power_dc_to_ac": [5.0],
        "max_power_ac_to_dc": [4.0],
    }

    result = inverter.adapter.build_config_data(loaded_values, config)

    assert result["element_type"] == "inverter"
    assert result["name"] == "test_inverter"
    np.testing.assert_array_equal(result["max_power_dc_to_ac"], [5.0])
    np.testing.assert_array_equal(result["max_power_ac_to_dc"], [4.0])


def test_build_config_data_includes_optional_efficiency() -> None:
    """build_config_data() should include optional efficiency fields when provided."""
    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
    }
    loaded_values = {
        "max_power_dc_to_ac": [5.0],
        "max_power_ac_to_dc": [4.0],
        "efficiency_dc_to_ac": 97.0,
        "efficiency_ac_to_dc": 95.0,
    }

    result = inverter.adapter.build_config_data(loaded_values, config)

    efficiency_dc_to_ac = result.get("efficiency_dc_to_ac")
    assert efficiency_dc_to_ac is not None
    np.testing.assert_array_equal(efficiency_dc_to_ac, 97.0)
    efficiency_ac_to_dc = result.get("efficiency_ac_to_dc")
    assert efficiency_ac_to_dc is not None
    np.testing.assert_array_equal(efficiency_ac_to_dc, 95.0)
