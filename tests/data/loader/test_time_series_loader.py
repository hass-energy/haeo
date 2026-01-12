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


async def test_time_series_loader_available_handles_missing_sensor(hass: HomeAssistant) -> None:
    """Loader is unavailable when any referenced sensor is missing."""

    loader = TimeSeriesLoader()

    # Missing sensor should make it unavailable
    assert loader.available(hass=hass, value=["sensor.missing"]) is False

    # Loading a missing sensor should raise an error
    with pytest.raises(ValueError, match=r"No time series data available"):
        await loader.load_intervals(hass=hass, value=["sensor.missing"], forecast_times=[0])


async def test_time_series_loader_accepts_constant_values(hass: HomeAssistant) -> None:
    """Loader accepts constant int and float values and broadcasts them."""

    loader = TimeSeriesLoader()

    # Integer constant should be accepted and broadcast
    result = await loader.load_intervals(hass=hass, value=123, forecast_times=[0, 1, 2])
    assert result == [123.0, 123.0]  # 3 boundaries = 2 periods

    # Float constant should be accepted and broadcast
    result = await loader.load_intervals(hass=hass, value=1.5, forecast_times=[0, 1, 2, 3])
    assert result == [1.5, 1.5, 1.5]  # 4 boundaries = 3 periods

    # Single boundary means 0 periods
    result = await loader.load_intervals(hass=hass, value=5.0, forecast_times=[0])
    assert result == []  # 1 boundary = 0 periods

    # Empty boundaries means 0 periods
    result = await loader.load_intervals(hass=hass, value=5.0, forecast_times=[])
    assert result == []

    # Constants are always available
    assert loader.available(hass=hass, value=123) is True
    assert loader.available(hass=hass, value=1.5) is True


async def test_time_series_loader_available_requires_valid_sensor_data(hass: HomeAssistant) -> None:
    """Sensors without valid data cause availability to fail."""

    loader = TimeSeriesLoader()

    # Set up a sensor with unavailable state
    hass.states.async_set("sensor.unavailable", "unavailable", {})

    # Should be unavailable when sensor state is invalid
    assert loader.available(hass=hass, value=["sensor.unavailable"]) is False

    # Loading should raise an error
    with pytest.raises(ValueError, match=r"No time series data available"):
        await loader.load_intervals(hass=hass, value=["sensor.unavailable"], forecast_times=[0])


async def test_time_series_loader_requires_sensor_entities(hass: HomeAssistant) -> None:
    """Load attempts fail when no sensor entities are provided."""

    loader = TimeSeriesLoader()

    assert loader.available(hass=hass, value=[]) is False

    with pytest.raises(ValueError, match="At least one sensor entity is required"):
        await loader.load_intervals(hass=hass, value=[], forecast_times=[1])


async def test_time_series_loader_loads_mixed_live_and_forecast(hass: HomeAssistant) -> None:
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

    with patch("custom_components.haeo.data.loader.sensor_loader.extract", side_effect=mock_extract):
        assert loader.available(hass=hass, value=["sensor.live_price", "sensor.forecast_price"]) is True

        result = await loader.load_intervals(
            hass=hass,
            value=["sensor.live_price", "sensor.forecast_price"],
            forecast_times=ts_values,
        )

    # Returns n_periods interval values (len(ts_values)-1)
    assert len(result) == len(ts_values) - 1
    assert all(isinstance(v, float) for v in result)


async def test_time_series_loader_returns_empty_series_for_empty_horizon(hass: HomeAssistant) -> None:
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

    assert await loader.load_intervals(hass=hass, value=["sensor.live_price"], forecast_times=[]) == []


# --- Tests for load_boundaries() ---


async def test_load_boundaries_returns_n_plus_1_values(hass: HomeAssistant) -> None:
    """load_boundaries returns n+1 values for n+1 boundary timestamps."""
    loader = TimeSeriesLoader()

    start = datetime(2024, 1, 1, tzinfo=UTC)
    # 3 boundary timestamps
    ts_values = [int((start + timedelta(hours=offset)).timestamp()) for offset in range(3)]

    def mock_extract(state: State) -> ExtractedData:
        # Forecast sensor returns data at boundary times
        return ExtractedData(
            data=[
                (int((start + timedelta(hours=0)).timestamp()), 10.0),
                (int((start + timedelta(hours=1)).timestamp()), 15.0),
                (int((start + timedelta(hours=2)).timestamp()), 20.0),
            ],
            unit="kWh",
        )

    hass.states.async_set("sensor.capacity", "10.0", {})

    with patch("custom_components.haeo.data.loader.sensor_loader.extract", side_effect=mock_extract):
        result = await loader.load_boundaries(
            hass=hass,
            value=["sensor.capacity"],
            forecast_times=ts_values,
        )

    # Returns n+1 values (one per boundary)
    assert len(result) == len(ts_values)
    assert all(isinstance(v, float) for v in result)


async def test_load_boundaries_broadcasts_constant_value(hass: HomeAssistant) -> None:
    """load_boundaries broadcasts constant value to n+1 positions."""
    loader = TimeSeriesLoader()
    ts_values = [1000.0, 2000.0, 3000.0, 4000.0]  # 4 boundaries

    result = await loader.load_boundaries(
        hass=hass,
        value=13.5,
        forecast_times=ts_values,
    )

    # Returns n+1 values, all equal to the constant
    assert len(result) == 4
    assert result == [13.5, 13.5, 13.5, 13.5]


async def test_load_boundaries_empty_horizon_returns_empty(hass: HomeAssistant) -> None:
    """load_boundaries returns empty list for empty horizon."""
    loader = TimeSeriesLoader()

    result = await loader.load_boundaries(
        hass=hass,
        value=10.0,
        forecast_times=[],
    )

    assert result == []


async def test_load_boundaries_raises_when_empty_entity_ids(hass: HomeAssistant) -> None:
    """load_boundaries raises ValueError when entity_ids list is empty."""
    loader = TimeSeriesLoader()
    ts_values = [1000.0, 2000.0, 3000.0]

    with pytest.raises(ValueError, match="At least one sensor entity is required"):
        await loader.load_boundaries(
            hass=hass,
            value=[],  # Empty list of entity IDs
            forecast_times=ts_values,
        )


async def test_load_boundaries_raises_when_no_data_available(hass: HomeAssistant) -> None:
    """load_boundaries raises ValueError when sensor state is unavailable."""
    loader = TimeSeriesLoader()
    ts_values = [1000.0, 2000.0, 3000.0]

    # Set up a sensor with unavailable state (same pattern as load_intervals test)
    hass.states.async_set("sensor.capacity", "unavailable", {})

    with pytest.raises(ValueError, match="No time series data available"):
        await loader.load_boundaries(
            hass=hass,
            value=["sensor.capacity"],
            forecast_times=ts_values,
        )


async def test_load_boundaries_raises_when_sensors_missing(hass: HomeAssistant) -> None:
    """load_boundaries raises ValueError when some sensors are unavailable."""
    loader = TimeSeriesLoader()
    ts_values = [1000.0, 2000.0, 3000.0]

    # One sensor with valid data, one with unavailable state
    hass.states.async_set("sensor.capacity1", "10.0")
    hass.states.async_set("sensor.capacity2", "unavailable", {})

    with pytest.raises(ValueError, match="Sensors not found or unavailable"):
        await loader.load_boundaries(
            hass=hass,
            value=["sensor.capacity1", "sensor.capacity2"],
            forecast_times=ts_values,
        )
