"""Tests for the historical load loader."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader.historical_load_loader import (
    HistoricalLoadLoader,
    build_forecast_from_history,
    get_energy_consumption_entities,
)


class TestGetEnergyConsumptionEntities:
    """Tests for get_energy_consumption_entities function."""

    @pytest.mark.asyncio
    async def test_returns_consumption_entities_from_energy_manager(self, hass: HomeAssistant) -> None:
        """Should return consumption entities from the Energy Manager."""
        mock_manager = MagicMock()
        mock_manager.data = {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {"stat_energy_from": "sensor.grid_consumption"},
                        {"stat_energy_from": "sensor.grid_consumption_2"},
                    ],
                    "flow_to": [{"stat_energy_to": "sensor.grid_export"}],
                },
                {
                    "type": "solar",
                    "stat_energy_from": "sensor.solar_production",
                },
            ]
        }

        with patch(
            "homeassistant.components.energy.data.async_get_manager",
            new=AsyncMock(return_value=mock_manager),
        ):
            result = await get_energy_consumption_entities(hass)

        assert result == ["sensor.grid_consumption", "sensor.grid_consumption_2"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_energy_sources(self, hass: HomeAssistant) -> None:
        """Should return empty list when no energy sources are configured."""
        mock_manager = MagicMock()
        mock_manager.data = {"energy_sources": []}

        with patch(
            "homeassistant.components.energy.data.async_get_manager",
            new=AsyncMock(return_value=mock_manager),
        ):
            result = await get_energy_consumption_entities(hass)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_manager_has_no_data(self, hass: HomeAssistant) -> None:
        """Should return empty list when manager has no data."""
        mock_manager = MagicMock()
        mock_manager.data = None

        with patch(
            "homeassistant.components.energy.data.async_get_manager",
            new=AsyncMock(return_value=mock_manager),
        ):
            result = await get_energy_consumption_entities(hass)

        assert result == []


class TestBuildForecastFromHistory:
    """Tests for build_forecast_from_history function."""

    def test_builds_forecast_from_statistics(self) -> None:
        """Should build a forecast series from historical statistics."""
        now = datetime.now(tz=UTC)
        hour_1 = now - timedelta(hours=2)
        hour_2 = now - timedelta(hours=1)

        statistics: Any = {
            "sensor.consumption": [
                {"start": hour_1, "change": 1.5},
                {"start": hour_2, "change": 2.0},
            ]
        }

        result = build_forecast_from_history(statistics, history_days=7)

        # Should have 2 data points
        assert len(result) == 2

        # Timestamps should be shifted forward by 7 days
        shift_seconds = 7 * 24 * 3600
        expected_ts_1 = hour_1.timestamp() + shift_seconds
        expected_ts_2 = hour_2.timestamp() + shift_seconds

        assert result[0][0] == pytest.approx(expected_ts_1)
        assert result[0][1] == 1.5
        assert result[1][0] == pytest.approx(expected_ts_2)
        assert result[1][1] == 2.0

    def test_sums_power_from_multiple_entities(self) -> None:
        """Should sum power values from multiple consumption entities."""
        now = datetime.now(tz=UTC)
        hour_1 = now - timedelta(hours=1)

        statistics: Any = {
            "sensor.consumption_1": [{"start": hour_1, "change": 1.0}],
            "sensor.consumption_2": [{"start": hour_1, "change": 0.5}],
        }

        result = build_forecast_from_history(statistics, history_days=7)

        assert len(result) == 1
        assert result[0][1] == 1.5  # Sum of 1.0 + 0.5

    def test_returns_empty_list_for_empty_statistics(self) -> None:
        """Should return empty list when no statistics are provided."""
        result = build_forecast_from_history({}, history_days=7)
        assert result == []

    def test_skips_entries_without_change(self) -> None:
        """Should skip entries without a change value."""
        now = datetime.now(tz=UTC)

        statistics: Any = {
            "sensor.consumption": [
                {"start": now - timedelta(hours=2), "change": 1.0},
                {"start": now - timedelta(hours=1), "change": None},
            ]
        }

        result = build_forecast_from_history(statistics, history_days=7)

        assert len(result) == 1
        assert result[0][1] == 1.0


class TestHistoricalLoadLoader:
    """Tests for HistoricalLoadLoader class."""

    def test_available_accepts_integer_value(self, hass: HomeAssistant) -> None:
        """Should accept integer values for history_days."""
        loader = HistoricalLoadLoader()
        assert loader.available(hass=hass, value=7) is True
        assert loader.available(hass=hass, value="7") is True
        assert loader.available(hass=hass, value=1) is True

    def test_available_rejects_invalid_value(self, hass: HomeAssistant) -> None:
        """Should reject non-integer values."""
        loader = HistoricalLoadLoader()
        assert loader.available(hass=hass, value="not_a_number") is False
        assert loader.available(hass=hass, value=None) is False

    @pytest.mark.asyncio
    async def test_load_returns_empty_for_empty_forecast_times(self, hass: HomeAssistant) -> None:
        """Should return empty list when forecast_times is empty."""
        loader = HistoricalLoadLoader()
        result = await loader.load(hass=hass, value=7, forecast_times=[])
        assert result == []

    @pytest.mark.asyncio
    async def test_load_raises_when_no_consumption_entities(self, hass: HomeAssistant) -> None:
        """Should raise ValueError when no consumption entities are configured."""
        loader = HistoricalLoadLoader()

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_consumption_entities",
                new=AsyncMock(return_value=[]),
            ),
            pytest.raises(ValueError, match="No consumption sensors configured"),
        ):
            await loader.load(hass=hass, value=7, forecast_times=[0, 3600, 7200])

    @pytest.mark.asyncio
    async def test_load_raises_when_no_historical_data(self, hass: HomeAssistant) -> None:
        """Should raise ValueError when no historical data is available."""
        loader = HistoricalLoadLoader()

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_consumption_entities",
                new=AsyncMock(return_value=["sensor.consumption"]),
            ),
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.fetch_historical_statistics",
                new=AsyncMock(return_value={}),
            ),
            pytest.raises(ValueError, match="No historical data available"),
        ):
            await loader.load(hass=hass, value=7, forecast_times=[0, 3600, 7200])

    @pytest.mark.asyncio
    async def test_load_returns_forecast_values(self, hass: HomeAssistant) -> None:
        """Should return forecast values aligned with forecast_times."""
        loader = HistoricalLoadLoader()

        # Create mock historical data
        now = datetime.now(tz=UTC)
        statistics = {
            "sensor.consumption": [
                {"start": now - timedelta(hours=2), "change": 1.0},
                {"start": now - timedelta(hours=1), "change": 2.0},
            ]
        }

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_consumption_entities",
                new=AsyncMock(return_value=["sensor.consumption"]),
            ),
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.fetch_historical_statistics",
                new=AsyncMock(return_value=statistics),
            ),
        ):
            result = await loader.load(
                hass=hass,
                value=7,
                forecast_times=[now.timestamp(), now.timestamp() + 3600, now.timestamp() + 7200],
            )

        # Should return 2 interval values (one less than fence-post timestamps)
        assert len(result) == 2
        assert all(isinstance(v, float) for v in result)
