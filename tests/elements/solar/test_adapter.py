"""Tests for solar adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import solar

from ..conftest import set_forecast_sensor


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Solar available() should return True when forecast sensor exists."""
    set_forecast_sensor(hass, "sensor.forecast", "5.0", [{"datetime": "2024-01-01T00:00:00Z", "value": 5.0}], "kW")

    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "common": {"name": "test_solar", "connection": "dc_bus"},
        "forecast": {"forecast": ["sensor.forecast"]},
        "pricing": {"price_source_target": 0.0},
        "curtailment": {"curtailment": True},
    }

    result = solar.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_forecast_sensor_missing(hass: HomeAssistant) -> None:
    """Solar available() should return False when forecast sensor is missing."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "common": {"name": "test_solar", "connection": "dc_bus"},
        "forecast": {"forecast": ["sensor.missing"]},
        "pricing": {"price_source_target": 0.0},
        "curtailment": {"curtailment": True},
    }

    result = solar.adapter.available(config, hass=hass)
    assert result is False
