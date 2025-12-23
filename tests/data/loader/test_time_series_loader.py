"""Integration tests for the time series loader with real Home Assistant state.

These tests verify the loader works correctly with actual Home Assistant state objects
and sensor data extraction. They focus on:
- Sensor availability checking
- Entity ID validation
- Error handling for missing/invalid sensors
- Integration with the full pipeline

Lower-level logic is tested in:
- test_time_series_loader_unit.py (entity ID handling, mocked sensors)
- tests/data/util/test_forecast_fuser.py (fusion logic)
- tests/data/util/test_forecast_cycle.py (cycling logic)
- tests/data/util/test_forecast_combiner.py (combining logic)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.haeo.data.loader.extractors import ExtractedData
from custom_components.haeo.data.loader.time_series_loader import TimeSeriesLoader


async def test_time_series_loader_available_handles_missing_sensor(
    hass: HomeAssistant,
) -> None:
    """Loader is unavailable when any referenced sensor is missing."""

    loader = TimeSeriesLoader()

    # Missing sensor should make it unavailable
    assert loader.available(hass=hass, value=["sensor.missing"]) is False

    # Loading a missing sensor should raise an error
    with pytest.raises(ValueError, match=r"No time series data available"):
        await loader.load(hass=hass, value=["sensor.missing"], forecast_times=[0])


async def test_time_series_loader_handles_constant_values(hass: HomeAssistant) -> None:
    """Loader accepts constant numeric values and returns them repeated for each timestamp."""

    loader = TimeSeriesLoader()

    # Constant values are valid and return the same value for each forecast time
    result = await loader.load(hass=hass, value=123.0, forecast_times=[0, 1, 2])
    assert result == [123.0, 123.0, 123.0]

    # Integer constants are also accepted
    result = await loader.load(hass=hass, value=42, forecast_times=[0, 1])
    assert result == [42.0, 42.0]

    # Constants with no forecast times return empty list
    result = await loader.load(hass=hass, value=99.0, forecast_times=[])
    assert result == []


async def test_time_series_loader_rejects_non_sequence_and_non_numeric_values(
    hass: HomeAssistant,
) -> None:
    """Loader rejects values that are neither sensor IDs nor numeric constants."""

    loader = TimeSeriesLoader()

    # Non-list, non-string, non-numeric values that can't be normalized raise TypeError
    with pytest.raises(TypeError, match="sensor entity IDs"):
        await loader.load(hass=hass, value=object(), forecast_times=[0])

    # Availability check also returns False for invalid types
    assert loader.available(hass=hass, value=object()) is False


async def test_time_series_loader_available_requires_valid_sensor_data(
    hass: HomeAssistant,
) -> None:
    """Sensors without valid data cause availability to fail."""

    loader = TimeSeriesLoader()

    # Set up a sensor with unavailable state
    hass.states.async_set("sensor.unavailable", "unavailable", {})

    # Should be unavailable when sensor state is invalid
    assert loader.available(hass=hass, value=["sensor.unavailable"]) is False

    # Loading should raise an error
    with pytest.raises(ValueError, match=r"No time series data available"):
        await loader.load(hass=hass, value=["sensor.unavailable"], forecast_times=[0])


async def test_time_series_loader_returns_none_when_no_entities(
    hass: HomeAssistant,
) -> None:
    """Load returns None when no sensor entities are provided."""

    loader = TimeSeriesLoader()

    assert loader.available(hass=hass, value=[]) is False

    result = await loader.load(hass=hass, value=[], forecast_times=[1])
    assert result is None


async def test_time_series_loader_loads_mixed_live_and_forecast(
    hass: HomeAssistant,
) -> None:
    """Loader combines live values with forecast series and aligns to the horizon."""

    loader = TimeSeriesLoader()

    start = datetime(2024, 1, 1, tzinfo=UTC)
    # Pass n+1 boundary timestamps (5 timestamps for 4 intervals)
    ts_values = [int((start + timedelta(hours=offset)).timestamp()) for offset in range(5)]

    # Mock extract to return different types of series
    def mock_extract(state: State) -> ExtractedData:
        if state.entity_id == "sensor.live_price":
            # Simple value returns as float
            return ExtractedData(data=0.2, unit="$/kWh")
        # Forecast sensor returns actual forecast data
        return ExtractedData(
            data=[
                (int((start + timedelta(hours=1)).timestamp()), 0.25),
                (int((start + timedelta(hours=2)).timestamp()), 0.35),
                (int((start + timedelta(hours=3)).timestamp()), 0.40),
            ],
            unit="$/kWh",
        )

    hass.states.async_set("sensor.live_price", "0.20", {})
    hass.states.async_set("sensor.forecast_price", "0.25", {})

    with patch(
        "custom_components.haeo.data.loader.sensor_loader.extract",
        side_effect=mock_extract,
    ):
        assert loader.available(hass=hass, value=["sensor.live_price", "sensor.forecast_price"]) is True

        result = await loader.load(
            hass=hass,
            value=["sensor.live_price", "sensor.forecast_price"],
            forecast_times=ts_values,
        )

    # Returns n_periods interval values (len(ts_values)-1)
    assert len(result) == len(ts_values) - 1
    assert all(isinstance(v, float) for v in result)


async def test_time_series_loader_returns_empty_series_for_empty_horizon(
    hass: HomeAssistant,
) -> None:
    """No forecast horizon results in an empty list without data access."""

    loader = TimeSeriesLoader()

    hass.states.async_set(
        "sensor.live_price",
        "0.20",
        {
            "device_class": SensorDeviceClass.MONETARY,
            "unit_of_measurement": "$/kWh",
        },
    )

    assert await loader.load(hass=hass, value=["sensor.live_price"], forecast_times=[]) == []
