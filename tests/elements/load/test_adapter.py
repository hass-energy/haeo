"""Tests for load element adapter load() and available() functions."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import load as load_element
from custom_components.haeo.elements.load.schema import DEFAULT_FORECAST

from ..conftest import FORECAST_TIMES, set_forecast_sensor, set_sensor


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


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Load load() should return ConfigData with loaded values."""
    set_sensor(hass, "sensor.power", "2.5", "kW")

    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.power"],
    }

    result = await load_element.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "load"
    assert result["name"] == "test_load"
    assert len(result["forecast"]) == 1
    assert result["forecast"][0] == 2.5


async def test_load_with_forecast_attribute(hass: HomeAssistant) -> None:
    """Load load() should work with forecast attribute data."""
    set_forecast_sensor(hass, "sensor.forecast_power", "2.5", [{"datetime": "2024-01-01T00:00:00Z", "value": 2.5}], "kW")

    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.forecast_power"],
    }

    result = await load_element.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "load"
    assert result["name"] == "test_load"
    assert len(result["forecast"]) == 1


async def test_available_returns_true_for_empty_forecast_list(hass: HomeAssistant) -> None:
    """Load available() should return True when forecast list is empty (uses default)."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": [],
    }

    result = load_element.adapter.available(config, hass=hass)
    assert result is True


async def test_load_with_empty_forecast_uses_default(hass: HomeAssistant) -> None:
    """Load load() should use default forecast values when forecast list is empty."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": [],
    }

    result = await load_element.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "load"
    assert result["name"] == "test_load"
    assert result["forecast"] == [DEFAULT_FORECAST, DEFAULT_FORECAST]
