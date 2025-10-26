"""Unit tests for ForecastLoader and ForecastAndSensorLoader."""

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import ForecastAndSensorLoader, ForecastLoader


async def test_forecast_loader_missing_sensor(hass: HomeAssistant) -> None:
    """Test ForecastLoader handles missing sensors."""
    loader = ForecastLoader()

    # Check availability first
    assert loader.available(hass=hass, value=["sensor.missing"], forecast_times=[]) is False

    # Try to load - should raise ValueError
    with pytest.raises(ValueError, match=r"Sensor sensor\.missing not found"):
        await loader.load(hass=hass, value=["sensor.missing"], forecast_times=[0, 3600])


async def test_forecast_loader_no_forecast_data(hass: HomeAssistant) -> None:
    """Test ForecastLoader handles sensors without forecast data."""
    loader = ForecastLoader()

    # Create sensor without forecast attributes
    hass.states.async_set(
        "sensor.no_forecast",
        "100",
        {"device_class": SensorDeviceClass.POWER, "unit_of_measurement": UnitOfPower.WATT},
    )

    # Should not be available (no forecast data)
    assert loader.available(hass=hass, value=["sensor.no_forecast"], forecast_times=[]) is False

    # Try to load - should raise ValueError about missing forecast data
    with pytest.raises(ValueError, match=r"No forecast data available for sensor"):
        await loader.load(hass=hass, value=["sensor.no_forecast"], forecast_times=[0, 3600])


async def test_forecast_loader_invalid_type(hass: HomeAssistant) -> None:
    """Test ForecastLoader handles invalid input types."""
    loader = ForecastLoader()

    # Test with number (not a sequence)
    assert loader.is_valid_value(123) is False

    # Test with sequence of non-strings
    assert loader.is_valid_value([1, 2, 3]) is False


async def test_forecast_loader_unavailable_state(hass: HomeAssistant) -> None:
    """Test ForecastLoader handles unavailable sensor states."""
    loader = ForecastLoader()

    hass.states.async_set("sensor.unavailable", "unavailable")

    # Should not be available
    assert loader.available(hass=hass, value=["sensor.unavailable"], forecast_times=[]) is False


async def test_forecast_and_sensor_loader_missing_sensor(hass: HomeAssistant) -> None:
    """Test ForecastAndSensorLoader handles missing sensors."""
    loader = ForecastAndSensorLoader()

    # Check availability first - missing sensor
    assert (
        loader.available(
            hass=hass,
            value={"live": ["sensor.missing"], "forecast": ["sensor.missing"]},
            forecast_times=[],
        )
        is False
    )


async def test_forecast_and_sensor_loader_invalid_type(hass: HomeAssistant) -> None:
    """Test ForecastAndSensorLoader type validation."""
    loader = ForecastAndSensorLoader()

    # Test is_valid_value with invalid types
    assert loader.is_valid_value("not_a_dict") is False
    assert loader.is_valid_value(123) is False
    assert loader.is_valid_value(["list"]) is False


async def test_forecast_and_sensor_loader_missing_keys(hass: HomeAssistant) -> None:
    """Test ForecastAndSensorLoader validates structure with TypeGuard."""
    loader = ForecastAndSensorLoader()

    # Test with missing 'live' key - is_valid_value should return False
    assert loader.is_valid_value({"forecast": ["sensor.test"]}) is False

    # Test with missing 'forecast' key - is_valid_value should return False
    assert loader.is_valid_value({"live": ["sensor.test"]}) is False

    # Test with both keys present and valid - is_valid_value should return True
    assert loader.is_valid_value({"live": ["sensor.test"], "forecast": ["sensor.forecast"]}) is True
