"""Tests for solar adapter load() and available() functions."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import solar

from ..conftest import FORECAST_TIMES, set_forecast_sensor


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Solar available() should return True when forecast sensor exists."""
    set_forecast_sensor(hass, "sensor.forecast", "5.0", [{"datetime": "2024-01-01T00:00:00Z", "value": 5.0}], "kW")

    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
    }

    result = solar.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_forecast_sensor_missing(hass: HomeAssistant) -> None:
    """Solar available() should return False when forecast sensor is missing."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.missing"],
    }

    result = solar.adapter.available(config, hass=hass)
    assert result is False


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Solar load() should return ConfigData with loaded values."""
    set_forecast_sensor(hass, "sensor.forecast", "5.0", [{"datetime": "2024-01-01T00:00:00Z", "value": 5.0}], "kW")

    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
    }

    result = await solar.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "solar"
    assert result["name"] == "test_solar"
    assert len(result["forecast"]) == 1


async def test_load_with_optional_fields(hass: HomeAssistant) -> None:
    """Solar load() should include optional fields."""
    set_forecast_sensor(hass, "sensor.forecast", "5.0", [{"datetime": "2024-01-01T00:00:00Z", "value": 5.0}], "kW")

    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
        "price_production": 0.02,
        "curtailment": False,
    }

    result = await solar.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    # price_production is now loaded as time series
    assert result.get("price_production") == [0.02]
    assert result.get("curtailment") is False
