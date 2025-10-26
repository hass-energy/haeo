"""Tests for ForecastAndSensorLoader."""

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.data.loader import ForecastAndSensorLoader, ForecastAndSensorValue


async def test_forecast_and_sensor_loader_type_guard(hass: HomeAssistant) -> None:
    """Test ForecastAndSensorLoader TypeGuard validation."""
    loader = ForecastAndSensorLoader()

    # Valid value
    valid_value: ForecastAndSensorValue = {
        "live": ["sensor.live"],
        "forecast": ["sensor.forecast"],
    }
    assert loader.is_valid_value(valid_value) is True

    # Missing 'live' key
    assert loader.is_valid_value({"forecast": ["sensor.forecast"]}) is False

    # Missing 'forecast' key
    assert loader.is_valid_value({"live": ["sensor.live"]}) is False

    # Wrong type for 'live' (not a sequence)
    assert loader.is_valid_value({"live": "sensor.live", "forecast": ["sensor.forecast"]}) is False

    # Wrong type for 'forecast' (not a sequence)
    assert loader.is_valid_value({"live": ["sensor.live"], "forecast": "sensor.forecast"}) is False

    # Not a dict
    assert loader.is_valid_value("not a dict") is False
    assert loader.is_valid_value(None) is False
    assert loader.is_valid_value([]) is False


async def test_forecast_and_sensor_loader_unavailable_live(hass: HomeAssistant) -> None:
    """Test availability when live sensor is unavailable."""
    loader = ForecastAndSensorLoader()

    # Set up forecast sensor (available)
    hass.states.async_set(
        "sensor.forecast_power",
        "1000",
        {
            "device_class": SensorDeviceClass.POWER,
            "unit_of_measurement": UnitOfPower.WATT,
            "forecast": [
                {"datetime": "2024-01-01T00:00:00Z", "power": 1000},
            ],
        },
    )

    # Live sensor is unavailable
    hass.states.async_set("sensor.live_power", "unavailable")

    value: ForecastAndSensorValue = {
        "live": ["sensor.live_power"],
        "forecast": ["sensor.forecast_power"],
    }

    forecast_times = [0]

    # Should not be available
    assert loader.available(hass=hass, value=value, forecast_times=forecast_times) is False


async def test_forecast_and_sensor_loader_unavailable_forecast(hass: HomeAssistant) -> None:
    """Test availability when forecast sensor is unavailable."""
    loader = ForecastAndSensorLoader()

    # Set up live sensor (available)
    hass.states.async_set(
        "sensor.live_power", "2000", {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT}
    )

    # Forecast sensor missing forecast attribute
    hass.states.async_set(
        "sensor.forecast_power",
        "1000",
        {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT},
    )

    value: ForecastAndSensorValue = {
        "live": ["sensor.live_power"],
        "forecast": ["sensor.forecast_power"],
    }

    forecast_times = [0]

    # Should not be available (forecast missing)
    assert loader.available(hass=hass, value=value, forecast_times=forecast_times) is False
