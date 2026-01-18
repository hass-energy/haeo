"""Tests for load element adapter build_config_data() and available() functions."""

import numpy as np
from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import load as load_element

from ..conftest import set_sensor


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Load available() should return True when forecast sensor exists."""
    set_sensor(hass, "sensor.power", "2.5", "kW")

    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.power"],
    }

    result = load_element.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_forecast_sensor_missing(hass: HomeAssistant) -> None:
    """Load available() should return False when forecast sensor is missing."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.missing"],
    }

    result = load_element.adapter.available(config, hass=hass)
    assert result is False


def test_build_config_data_returns_config_data() -> None:
    """build_config_data() should return ConfigData with loaded values."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.power"],
    }
    loaded_values = {"forecast": [2.5]}

    result = load_element.adapter.build_config_data(loaded_values, config)

    assert result["element_type"] == "load"
    assert result["name"] == "test_load"
    np.testing.assert_array_equal(result["forecast"], [2.5])


def test_inputs_returns_input_fields() -> None:
    """inputs() should return input field definitions for load."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.power"],
    }

    input_fields = load_element.adapter.inputs(config)

    assert "forecast" in input_fields
