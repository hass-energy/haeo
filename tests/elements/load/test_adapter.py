"""Tests for load element adapter load() and available() functions."""

from collections.abc import Sequence
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import load as load_element


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


def _set_forecast_sensor(
    hass: HomeAssistant, entity_id: str, value: str, forecast: list[dict[str, Any]], unit: str = "kW"
) -> None:
    """Set a sensor state with forecast attribute in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit, "forecast": forecast})


FORECAST_TIMES: Sequence[float] = [0.0, 1800.0]


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Load available() should return True when forecast sensor exists."""
    _set_sensor(hass, "sensor.power", "2.5", "kW")

    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.power"],
    }

    result = load_element.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_forecast_sensor_missing(hass: HomeAssistant) -> None:
    """Load available() should return False when forecast sensor is missing."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.missing"],
    }

    result = load_element.available(config, hass=hass)
    assert result is False


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Load load() should return ConfigData with loaded values."""
    _set_sensor(hass, "sensor.power", "2.5", "kW")

    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.power"],
    }

    result = await load_element.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "load"
    assert result["name"] == "test_load"
    assert len(result["forecast"]) == 1
    assert result["forecast"][0] == 2.5


async def test_load_with_forecast_attribute(hass: HomeAssistant) -> None:
    """Load load() should work with forecast attribute data."""
    _set_forecast_sensor(
        hass,
        "sensor.forecast_power",
        "2.5",
        [{"datetime": "2024-01-01T00:00:00Z", "value": 2.5}],
        "kW",
    )

    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.forecast_power"],
    }

    result = await load_element.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "load"
    assert result["name"] == "test_load"
    assert len(result["forecast"]) == 1
