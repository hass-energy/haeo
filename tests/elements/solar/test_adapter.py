"""Tests for solar adapter build_config_data() and available() functions."""

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.elements import solar

from ..conftest import set_forecast_sensor


def _assert_array_equal(actual: np.ndarray | None, expected: float | list[float]) -> None:
    assert actual is not None
    np.testing.assert_array_equal(actual, expected)


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Solar available() should return True when forecast sensor exists."""
    set_forecast_sensor(hass, "sensor.forecast", "5.0", [{"datetime": "2024-01-01T00:00:00Z", "value": 5.0}], "kW")

    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
        "curtailment": True,
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
        "curtailment": True,
    }

    result = solar.adapter.available(config, hass=hass)
    assert result is False


def test_build_config_data_returns_config_data() -> None:
    """build_config_data() should return ConfigData with loaded values."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
        "curtailment": True,
    }
    loaded_values = {
        "forecast": [5.0],
        "curtailment": True,
    }

    result = solar.adapter.build_config_data(loaded_values, config)

    assert result["element_type"] == "solar"
    assert result["name"] == "test_solar"
    assert result["forecast"] == [5.0]
    assert result.get("curtailment") is True


def test_build_config_data_includes_optional_fields() -> None:
    """build_config_data() should include optional constant fields when provided."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
        "price_production": 0.02,
        "curtailment": False,
    }
    loaded_values = {
        "forecast": [5.0],
        "price_production": [0.02],
        "curtailment": False,
    }

    result = solar.adapter.build_config_data(loaded_values, config)

    _assert_array_equal(result.get("price_production"), [0.02])
    assert result.get("curtailment") is False
