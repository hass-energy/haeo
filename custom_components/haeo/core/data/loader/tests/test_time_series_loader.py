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

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.extractors import ExtractedData
from custom_components.haeo.core.data.loader.time_series_loader import TimeSeriesLoader
from custom_components.haeo.core.schema import as_entity_value


async def test_time_series_loader_available_handles_missing_sensor() -> None:
    """Loader is unavailable when any referenced sensor is missing."""

    loader = TimeSeriesLoader()

    # Missing sensor should make it unavailable
    assert loader.available(sm=FakeStateMachine({}), value=as_entity_value(["sensor.missing"])) is False

    # Loading a missing sensor should raise an error
    with pytest.raises(ValueError, match=r"No time series data available"):
        await loader.load_intervals(
            sm=FakeStateMachine({}), value=as_entity_value(["sensor.missing"]), forecast_times=[0]
        )


async def test_time_series_loader_available_requires_valid_sensor_data() -> None:
    """Sensors without valid data cause availability to fail."""

    loader = TimeSeriesLoader()

    sm = FakeStateMachine(
        {
            "sensor.unavailable": FakeEntityState(
                entity_id="sensor.unavailable",
                state="unavailable",
                attributes={},
            )
        }
    )

    # Should be unavailable when sensor state is invalid
    assert loader.available(sm=sm, value=as_entity_value(["sensor.unavailable"])) is False

    # Loading should raise an error
    with pytest.raises(ValueError, match=r"No time series data available"):
        await loader.load_intervals(sm=sm, value=as_entity_value(["sensor.unavailable"]), forecast_times=[0])


async def test_time_series_loader_requires_sensor_entities() -> None:
    """Load attempts fail when no sensor entities are provided."""

    loader = TimeSeriesLoader()

    assert loader.available(sm=FakeStateMachine({}), value=as_entity_value([])) is False

    with pytest.raises(ValueError, match="At least one sensor entity is required"):
        await loader.load_intervals(sm=FakeStateMachine({}), value=as_entity_value([]), forecast_times=[1])


async def test_time_series_loader_loads_mixed_live_and_forecast() -> None:
    """Loader combines live values with forecast series and aligns to the horizon."""

    loader = TimeSeriesLoader()

    start = datetime(2024, 1, 1, tzinfo=UTC)
    # Pass n+1 boundary timestamps (5 timestamps for 4 intervals)
    ts_values = [int((start + timedelta(hours=offset)).timestamp()) for offset in range(5)]

    # Mock extract to return different types of series
    def mock_extract(state: FakeEntityState) -> ExtractedData:
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

    sm = FakeStateMachine(
        {
            "sensor.live_price": FakeEntityState(
                entity_id="sensor.live_price",
                state="0.20",
                attributes={},
            ),
            "sensor.forecast_price": FakeEntityState(
                entity_id="sensor.forecast_price",
                state="0.25",
                attributes={},
            ),
        }
    )

    with patch("custom_components.haeo.core.data.loader.sensor_loader.extract", side_effect=mock_extract):
        assert (
            loader.available(
                sm=sm,
                value=as_entity_value(["sensor.live_price", "sensor.forecast_price"]),
            )
            is True
        )

        result = await loader.load_intervals(
            sm=sm,
            value=as_entity_value(["sensor.live_price", "sensor.forecast_price"]),
            forecast_times=ts_values,
        )

    # Returns n_periods interval values (len(ts_values)-1)
    assert len(result) == len(ts_values) - 1
    assert all(isinstance(v, float) for v in result)


async def test_time_series_loader_returns_empty_series_for_empty_horizon() -> None:
    """No forecast horizon results in an empty list without data access."""

    loader = TimeSeriesLoader()

    sm = FakeStateMachine(
        {
            "sensor.live_price": FakeEntityState(
                entity_id="sensor.live_price",
                state="0.20",
                attributes={"device_class": "monetary", "unit_of_measurement": "$/kWh"},
            )
        }
    )

    assert (
        await loader.load_intervals(
            sm=sm,
            value=as_entity_value(["sensor.live_price"]),
            forecast_times=[],
        )
        == []
    )


# --- Tests for load_boundaries() ---


async def test_load_boundaries_returns_n_plus_1_values() -> None:
    """load_boundaries returns n+1 values for n+1 boundary timestamps."""
    loader = TimeSeriesLoader()

    start = datetime(2024, 1, 1, tzinfo=UTC)
    # 3 boundary timestamps
    ts_values = [int((start + timedelta(hours=offset)).timestamp()) for offset in range(3)]

    def mock_extract(state: FakeEntityState) -> ExtractedData:
        # Forecast sensor returns data at boundary times
        return ExtractedData(
            data=[
                (int((start + timedelta(hours=0)).timestamp()), 10.0),
                (int((start + timedelta(hours=1)).timestamp()), 15.0),
                (int((start + timedelta(hours=2)).timestamp()), 20.0),
            ],
            unit="kWh",
        )

    sm = FakeStateMachine(
        {
            "sensor.capacity": FakeEntityState(
                entity_id="sensor.capacity",
                state="10.0",
                attributes={},
            )
        }
    )

    with patch("custom_components.haeo.core.data.loader.sensor_loader.extract", side_effect=mock_extract):
        result = await loader.load_boundaries(
            sm=sm,
            value=as_entity_value(["sensor.capacity"]),
            forecast_times=ts_values,
        )

    # Returns n+1 values (one per boundary)
    assert len(result) == len(ts_values)
    assert all(isinstance(v, float) for v in result)


async def test_load_boundaries_empty_horizon_returns_empty() -> None:
    """load_boundaries returns empty list for empty horizon."""
    loader = TimeSeriesLoader()

    result = await loader.load_boundaries(
        sm=FakeStateMachine({}),
        value=as_entity_value(["sensor.capacity"]),
        forecast_times=[],
    )

    assert result == []


async def test_load_boundaries_raises_when_empty_entity_ids() -> None:
    """load_boundaries raises ValueError when entity_ids list is empty."""
    loader = TimeSeriesLoader()
    ts_values = [1000.0, 2000.0, 3000.0]

    with pytest.raises(ValueError, match="At least one sensor entity is required"):
        await loader.load_boundaries(
            sm=FakeStateMachine({}),
            value=as_entity_value([]),
            forecast_times=ts_values,
        )


async def test_load_boundaries_raises_when_no_data_available() -> None:
    """load_boundaries raises ValueError when sensor state is unavailable."""
    loader = TimeSeriesLoader()
    ts_values = [1000.0, 2000.0, 3000.0]

    sm = FakeStateMachine(
        {
            "sensor.capacity": FakeEntityState(
                entity_id="sensor.capacity",
                state="unavailable",
                attributes={},
            )
        }
    )

    with pytest.raises(ValueError, match="No time series data available"):
        await loader.load_boundaries(
            sm=sm,
            value=as_entity_value(["sensor.capacity"]),
            forecast_times=ts_values,
        )


async def test_load_boundaries_raises_when_sensors_missing() -> None:
    """load_boundaries raises ValueError when some sensors are unavailable."""
    loader = TimeSeriesLoader()
    ts_values = [1000.0, 2000.0, 3000.0]

    sm = FakeStateMachine(
        {
            "sensor.capacity1": FakeEntityState(
                entity_id="sensor.capacity1",
                state="10.0",
                attributes={},
            ),
            "sensor.capacity2": FakeEntityState(
                entity_id="sensor.capacity2",
                state="unavailable",
                attributes={},
            ),
        }
    )

    with pytest.raises(ValueError, match="Sensors not found or unavailable"):
        await loader.load_boundaries(
            sm=sm,
            value=as_entity_value(["sensor.capacity1", "sensor.capacity2"]),
            forecast_times=ts_values,
        )
