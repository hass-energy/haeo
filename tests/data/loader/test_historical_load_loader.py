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
    shift_history_to_forecast,
)


class TestShiftHistoryToForecast:
    """Tests for shift_history_to_forecast function."""

    def test_shifts_timestamps_forward(self) -> None:
        """Shifts historical timestamps forward by N days."""
        base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        stats = [
            {"start": base, "mean": 2.0},
            {"start": base + timedelta(hours=1), "mean": 3.0},
        ]

        result = shift_history_to_forecast(stats, history_days=7)

        # Should have 2 forecast points
        assert len(result) == 2

        # Timestamps should be shifted forward by 7 days
        expected_base = base + timedelta(days=7)
        assert result[0][0] == pytest.approx(expected_base.timestamp())
        assert result[1][0] == pytest.approx((expected_base + timedelta(hours=1)).timestamp())

        # Values should be unchanged
        assert result[0][1] == pytest.approx(2.0)
        assert result[1][1] == pytest.approx(3.0)

    def test_returns_empty_for_no_statistics(self) -> None:
        """Returns empty list when no statistics provided."""
        result = shift_history_to_forecast([], history_days=7)
        assert result == []

    def test_skips_entries_with_missing_values(self) -> None:
        """Skips entries without start or mean values."""
        base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        stats = [
            {"start": base, "mean": 2.0},
            {"start": base + timedelta(hours=1), "mean": None},  # Missing mean
            {"start": None, "mean": 3.0},  # Missing start
        ]

        result = shift_history_to_forecast(stats, history_days=7)

        # Only the first entry should be included
        assert len(result) == 1
        assert result[0][1] == pytest.approx(2.0)

    def test_handles_timestamp_as_float(self) -> None:
        """Handles statistics with timestamp as float."""
        base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        stats = [
            {"start": base.timestamp(), "mean": 5.0},
        ]

        result = shift_history_to_forecast(stats, history_days=7)

        assert len(result) == 1
        expected_time = (base + timedelta(days=7)).timestamp()
        assert result[0][0] == pytest.approx(expected_time)
        assert result[0][1] == pytest.approx(5.0)

    def test_sorts_by_timestamp(self) -> None:
        """Sorts results by timestamp."""
        base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        # Provide out-of-order statistics
        stats = [
            {"start": base + timedelta(hours=2), "mean": 3.0},
            {"start": base, "mean": 1.0},
            {"start": base + timedelta(hours=1), "mean": 2.0},
        ]

        result = shift_history_to_forecast(stats, history_days=7)

        # Should be sorted by timestamp
        assert result[0][1] == pytest.approx(1.0)
        assert result[1][1] == pytest.approx(2.0)
        assert result[2][1] == pytest.approx(3.0)


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
        hass.states.async_set("sensor.test", "5.0")

        loader = HistoricalForecastLoader()
        assert loader.available(hass=hass, value="sensor.test")

    def test_not_available_when_recorder_missing(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """available() returns False when recorder is not loaded."""
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
    async def test_load_shifts_history_forward(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """load() fetches statistics and shifts them forward to create forecast."""
        loader = HistoricalForecastLoader(history_days=7)
        tz = dt_util.get_default_time_zone()

        # Historical data from Jan 1-7
        history_base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=tz)
        mock_stats: list[dict[str, Any]] = [
            {"start": history_base, "mean": 100.0},
            {"start": history_base + timedelta(hours=1), "mean": 200.0},
        ]

        async def mock_get_stats(
            _hass: HomeAssistant,
            _entity_id: str,
            _start_time: datetime,
            _end_time: datetime,
        ) -> list[dict[str, Any]]:
            return mock_stats

        monkeypatch.setattr(hll, "get_statistics_for_sensor", mock_get_stats)

        # Request forecast for Jan 8 (7 days after history)
        forecast_base = datetime(2024, 1, 8, 10, 0, 0, tzinfo=tz)
        forecast_times = [
            forecast_base.timestamp(),
            (forecast_base + timedelta(hours=1)).timestamp(),
            (forecast_base + timedelta(hours=2)).timestamp(),
        ]

        result = await loader.load(hass=hass, value="sensor.test", forecast_times=forecast_times)

        # Should return 2 values (n-1 intervals)
        assert len(result) == 2
        # Values should match the shifted historical data
        assert result[0] == pytest.approx(100.0)  # from history at 10:00
        assert result[1] == pytest.approx(200.0)  # from history at 11:00

    @pytest.mark.asyncio
    async def test_load_sums_multiple_sensors(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """load() sums values from multiple sensors at the same timestamp."""
        loader = HistoricalForecastLoader(history_days=7)
        tz = dt_util.get_default_time_zone()

        history_base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=tz)
        call_count = 0

        async def mock_get_stats(
            _hass: HomeAssistant,
            entity_id: str,
            _start_time: datetime,
            _end_time: datetime,
        ) -> list[dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            value = 2.0 if "sensor1" in entity_id else 3.0
            return [{"start": history_base, "mean": value}]

        monkeypatch.setattr(hll, "get_statistics_for_sensor", mock_get_stats)

        forecast_base = datetime(2024, 1, 8, 10, 0, 0, tzinfo=tz)
        forecast_times = [forecast_base.timestamp(), (forecast_base + timedelta(hours=1)).timestamp()]

        result = await loader.load(
            hass=hass,
            value=["sensor.sensor1", "sensor.sensor2"],
            forecast_times=forecast_times,
        )

        assert call_count == 2
        assert len(result) == 1
        # Values should be summed: 2.0 + 3.0 = 5.0
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
            return [{"start": datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC), "mean": 5.0}]

        monkeypatch.setattr(hll, "get_statistics_for_sensor", mock_get_stats)

        base = datetime(2024, 1, 8, 10, 0, 0, tzinfo=UTC)
        await loader.load(
            hass=hass,
            value="sensor.my_sensor",
            forecast_times=[base.timestamp(), (base + timedelta(hours=1)).timestamp()],
        )

        assert captured_entity_id == "sensor.my_sensor"
