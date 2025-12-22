"""Tests for historical forecast loader.

Tests building forecasts from sensor historical statistics when a sensor
doesn't have a forecast attribute.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest

from custom_components.haeo.data.loader import historical_load_loader as hll
from custom_components.haeo.data.loader.historical_load_loader import (
    DEFAULT_HISTORY_DAYS,
    HistoricalForecastLoader,
    build_forecast_from_pattern,
    build_hourly_pattern,
)


class TestBuildHourlyPattern:
    """Tests for build_hourly_pattern function."""

    def test_builds_pattern_from_statistics(self) -> None:
        """Builds a 24-hour pattern by averaging values for each hour."""
        # Create statistics for hour 10 on two different days
        stats = [
            {"start": datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC), "mean": 2.0},
            {"start": datetime(2024, 1, 2, 10, 0, 0, tzinfo=UTC), "mean": 4.0},
            {"start": datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC), "mean": 3.0},
        ]

        # Use UTC timezone so hours match what we expect
        pattern = build_hourly_pattern(stats, timezone=UTC)

        # Hour 10 should be average of 2.0 and 4.0 = 3.0
        assert pattern[10] == pytest.approx(3.0)
        # Hour 14 should be 3.0
        assert pattern[14] == pytest.approx(3.0)

    def test_returns_empty_when_no_statistics(self) -> None:
        """Returns empty dict when no statistics provided."""
        pattern = build_hourly_pattern([])
        assert pattern == {}

    def test_handles_missing_mean_values(self) -> None:
        """Skips entries without mean values."""
        stats = [
            {"start": datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC), "mean": 2.0},
            {"start": datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC), "mean": None},
        ]

        pattern = build_hourly_pattern(stats, timezone=UTC)

        assert 10 in pattern
        assert 11 not in pattern

    def test_handles_timestamp_as_float(self) -> None:
        """Handles statistics with timestamp as float."""
        # Use a timestamp for hour 15 UTC
        ts = datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC).timestamp()
        stats = [
            {"start": ts, "mean": 5.0},
        ]

        # Use UTC so we know what hour to expect
        pattern = build_hourly_pattern(stats, timezone=UTC)

        assert len(pattern) == 1
        assert pattern[15] == pytest.approx(5.0)


class TestBuildForecastFromPattern:
    """Tests for build_forecast_from_pattern function."""

    def test_builds_forecast_for_each_interval(self) -> None:
        """Generates values for n-1 intervals from n timestamps."""
        hourly_pattern = {
            10: 2.0,
            11: 3.0,
            12: 4.0,
        }

        # 3 timestamps = 2 intervals
        base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        forecast_times = [
            base.timestamp(),
            (base + timedelta(hours=1)).timestamp(),
            (base + timedelta(hours=2)).timestamp(),
        ]

        result = build_forecast_from_pattern(hourly_pattern, forecast_times, timezone=UTC)

        assert len(result) == 2
        assert result[0] == pytest.approx(2.0)  # hour 10
        assert result[1] == pytest.approx(3.0)  # hour 11

    def test_returns_empty_for_insufficient_timestamps(self) -> None:
        """Returns empty list when less than 2 timestamps provided."""
        hourly_pattern = {10: 2.0}

        assert build_forecast_from_pattern(hourly_pattern, []) == []
        assert build_forecast_from_pattern(hourly_pattern, [1234567890.0]) == []

    def test_returns_zeros_for_empty_pattern(self) -> None:
        """Returns zeros when pattern is empty."""
        forecast_times = [0.0, 3600.0, 7200.0]

        result = build_forecast_from_pattern({}, forecast_times)

        assert result == [0.0, 0.0]

    def test_uses_zero_for_missing_hours(self) -> None:
        """Returns 0 for hours not in the pattern."""
        hourly_pattern = {10: 2.0}  # Only hour 10

        # Request hour 15 (not in pattern)
        base = datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC)
        forecast_times = [base.timestamp(), (base + timedelta(hours=1)).timestamp()]

        result = build_forecast_from_pattern(hourly_pattern, forecast_times, timezone=UTC)

        assert result == [0.0]


class TestHistoricalForecastLoader:
    """Tests for HistoricalForecastLoader class."""

    def test_default_history_days(self) -> None:
        """Loader uses default history days when not specified."""
        loader = HistoricalForecastLoader()
        assert loader._history_days == DEFAULT_HISTORY_DAYS

    def test_custom_history_days(self) -> None:
        """Loader respects custom history days."""
        loader = HistoricalForecastLoader(history_days=14)
        assert loader._history_days == 14

    def test_available_when_recorder_loaded_and_sensor_exists(self, hass: HomeAssistant) -> None:
        """available() returns True when recorder is loaded and sensor exists."""
        hass.config.components.add("recorder")

        # Create a real sensor state
        hass.states.async_set("sensor.test", "5.0")

        loader = HistoricalForecastLoader()

        assert loader.available(hass=hass, value="sensor.test")

    def test_not_available_when_recorder_missing(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """available() returns False when recorder is not loaded."""
        # Mock the __contains__ check to return False for "recorder"
        monkeypatch.setattr(
            hass.config.components,
            "__contains__",
            lambda component: component != "recorder",
        )
        loader = HistoricalForecastLoader()
        assert not loader.available(hass=hass, value="sensor.test")

    def test_not_available_when_sensor_missing(self, hass: HomeAssistant) -> None:
        """available() returns False when sensor doesn't exist."""
        hass.config.components.add("recorder")

        loader = HistoricalForecastLoader()

        # Sensor doesn't exist, so available should return False
        assert not loader.available(hass=hass, value="sensor.nonexistent")

    @pytest.mark.asyncio
    async def test_load_returns_empty_for_empty_forecast_times(self, hass: HomeAssistant) -> None:
        """load() returns empty list when forecast_times is empty."""
        loader = HistoricalForecastLoader()

        result = await loader.load(hass=hass, value="sensor.test", forecast_times=[])

        assert result == []

    @pytest.mark.asyncio
    async def test_load_raises_when_no_entity_ids(self, hass: HomeAssistant) -> None:
        """load() raises when no entity IDs provided."""
        loader = HistoricalForecastLoader()

        with pytest.raises(ValueError, match="No sensor entity IDs provided"):
            await loader.load(hass=hass, value=[], forecast_times=[0.0, 3600.0])

    @pytest.mark.asyncio
    async def test_load_builds_forecast_from_history(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load() fetches statistics and builds forecast from hourly pattern."""
        loader = HistoricalForecastLoader(history_days=7)

        # Use HA's default timezone for consistency
        tz = dt_util.get_default_time_zone()

        # Create mock statistics - 7 days of data for hours 10, 11, 12 in HA timezone
        mock_stats: list[dict[str, Any]] = []
        mock_stats.extend(
            {
                "start": datetime(2024, 1, 1 + day, hour, 0, 0, tzinfo=tz),
                "mean": float(hour),  # Use hour as the value for easy verification
            }
            for day in range(7)
            for hour in [10, 11, 12]
        )

        async def mock_get_stats(
            _hass: HomeAssistant,
            _entity_id: str,
            _start_time: datetime,
            _end_time: datetime,
        ) -> list[dict[str, Any]]:
            return mock_stats

        monkeypatch.setattr(hll, "get_statistics_for_sensor", mock_get_stats)

        # Create forecast times for hours 10, 11, 12 in HA timezone (3 timestamps = 2 intervals)
        base = datetime(2024, 1, 8, 10, 0, 0, tzinfo=tz)
        forecast_times = [
            base.timestamp(),
            (base + timedelta(hours=1)).timestamp(),
            (base + timedelta(hours=2)).timestamp(),
        ]

        result = await loader.load(hass=hass, value="sensor.test", forecast_times=forecast_times)

        # Should return 2 values (n-1 intervals)
        assert len(result) == 2
        # Values should match the hourly pattern (hour number as value)
        assert result[0] == pytest.approx(10.0)  # hour 10
        assert result[1] == pytest.approx(11.0)  # hour 11

    @pytest.mark.asyncio
    async def test_load_sums_multiple_sensors(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """load() sums values from multiple sensors."""
        loader = HistoricalForecastLoader(history_days=7)
        tz = dt_util.get_default_time_zone()

        call_count = 0

        async def mock_get_stats(
            _hass: HomeAssistant,
            entity_id: str,
            _start_time: datetime,
            _end_time: datetime,
        ) -> list[dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            # Return different values for each sensor
            value = 2.0 if "sensor1" in entity_id else 3.0
            return [
                {"start": datetime(2024, 1, 1, 10, 0, 0, tzinfo=tz), "mean": value},
            ]

        monkeypatch.setattr(hll, "get_statistics_for_sensor", mock_get_stats)

        base = datetime(2024, 1, 8, 10, 0, 0, tzinfo=tz)
        forecast_times = [base.timestamp(), (base + timedelta(hours=1)).timestamp()]

        result = await loader.load(
            hass=hass,
            value=["sensor.sensor1", "sensor.sensor2"],
            forecast_times=forecast_times,
        )

        # Should have called for both sensors
        assert call_count == 2
        # Values should be summed: 2.0 + 3.0 = 5.0
        assert len(result) == 1
        assert result[0] == pytest.approx(5.0)

    @pytest.mark.asyncio
    async def test_load_raises_when_no_historical_data(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load() raises when no historical data is available."""
        loader = HistoricalForecastLoader()

        async def mock_get_stats(
            _hass: HomeAssistant,
            _entity_id: str,
            _start_time: datetime,
            _end_time: datetime,
        ) -> list[dict[str, Any]]:
            return []

        monkeypatch.setattr(hll, "get_statistics_for_sensor", mock_get_stats)

        with pytest.raises(ValueError, match="No historical data available"):
            await loader.load(
                hass=hass,
                value="sensor.test",
                forecast_times=[0.0, 3600.0],
            )

    @pytest.mark.asyncio
    async def test_load_handles_string_entity_id(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """load() accepts a single string entity ID."""
        loader = HistoricalForecastLoader()

        captured_entity_id: str | None = None

        async def mock_get_stats(
            _hass: HomeAssistant,
            entity_id: str,
            _start_time: datetime,
            _end_time: datetime,
        ) -> list[dict[str, Any]]:
            nonlocal captured_entity_id
            captured_entity_id = entity_id
            return [
                {"start": datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC), "mean": 5.0},
            ]

        monkeypatch.setattr(hll, "get_statistics_for_sensor", mock_get_stats)

        base = datetime(2024, 1, 8, 10, 0, 0, tzinfo=UTC)
        await loader.load(
            hass=hass,
            value="sensor.my_sensor",
            forecast_times=[base.timestamp(), (base + timedelta(hours=1)).timestamp()],
        )

        assert captured_entity_id == "sensor.my_sensor"
