"""Tests for load element adapter available() and inputs() functions."""

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


def test_inputs_returns_input_field_info() -> None:
    """Load inputs() should return INPUT_FIELDS tuple."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.power"],
    }

    result = load_element.adapter.inputs(config)

    assert result == load_element.INPUT_FIELDS
    assert len(result) == 1
    assert result[0].field_name == "forecast"
