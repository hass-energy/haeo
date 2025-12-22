"""Tests for historical load loader.

Tests the calculation of total consumption from energy flows:
    Total Load = Grid Import + Solar Production - Grid Export
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import historical_load_loader as hll
from custom_components.haeo.data.loader.historical_load_loader import (
    DEFAULT_HISTORY_DAYS,
    EnergyEntities,
    HistoricalLoadLoader,
    build_forecast_from_history,
    get_energy_entities,
)


@pytest.fixture
def mock_energy_module() -> MagicMock:
    """Create a mock energy.data module."""
    return MagicMock()


class TestGetEnergyEntities:
    """Tests for get_energy_entities function."""

    @pytest.mark.asyncio
    async def test_extracts_grid_import_entities(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Grid import entities are extracted from flow_from entries."""
        mock_manager = MagicMock()
        mock_manager.data = {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {"stat_energy_from": "sensor.grid_import"},
                    ],
                    "flow_to": [],
                },
            ],
        }

        async def mock_get_manager(_hass: HomeAssistant) -> MagicMock:
            return mock_manager

        # Patch the import inside the function by patching the module import
        import sys

        mock_energy_data = MagicMock()
        mock_energy_data.async_get_manager = mock_get_manager
        monkeypatch.setitem(sys.modules, "homeassistant.components.energy.data", mock_energy_data)

        result = await get_energy_entities(hass)

        assert result["grid_import"] == ["sensor.grid_import"]
        assert result["grid_export"] == []
        assert result["solar"] == []

    @pytest.mark.asyncio
    async def test_extracts_grid_export_entities(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Grid export entities are extracted from flow_to entries."""
        mock_manager = MagicMock()
        mock_manager.data = {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [],
                    "flow_to": [
                        {"stat_energy_to": "sensor.grid_export"},
                    ],
                },
            ],
        }

        async def mock_get_manager(_hass: HomeAssistant) -> MagicMock:
            return mock_manager

        import sys

        mock_energy_data = MagicMock()
        mock_energy_data.async_get_manager = mock_get_manager
        monkeypatch.setitem(sys.modules, "homeassistant.components.energy.data", mock_energy_data)

        result = await get_energy_entities(hass)

        assert result["grid_import"] == []
        assert result["grid_export"] == ["sensor.grid_export"]
        assert result["solar"] == []

    @pytest.mark.asyncio
    async def test_extracts_solar_entities(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Solar entities are extracted from solar type sources."""
        mock_manager = MagicMock()
        mock_manager.data = {
            "energy_sources": [
                {
                    "type": "solar",
                    "stat_energy_from": "sensor.solar_production",
                },
            ],
        }

        async def mock_get_manager(_hass: HomeAssistant) -> MagicMock:
            return mock_manager

        import sys

        mock_energy_data = MagicMock()
        mock_energy_data.async_get_manager = mock_get_manager
        monkeypatch.setitem(sys.modules, "homeassistant.components.energy.data", mock_energy_data)

        result = await get_energy_entities(hass)

        assert result["grid_import"] == []
        assert result["grid_export"] == []
        assert result["solar"] == ["sensor.solar_production"]

    @pytest.mark.asyncio
    async def test_extracts_all_entity_types(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All entity types are extracted from a complete configuration."""
        mock_manager = MagicMock()
        mock_manager.data = {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {"stat_energy_from": "sensor.grid_import_1"},
                        {"stat_energy_from": "sensor.grid_import_2"},
                    ],
                    "flow_to": [
                        {"stat_energy_to": "sensor.grid_export"},
                    ],
                },
                {
                    "type": "solar",
                    "stat_energy_from": "sensor.solar_east",
                },
                {
                    "type": "solar",
                    "stat_energy_from": "sensor.solar_west",
                },
            ],
        }

        async def mock_get_manager(_hass: HomeAssistant) -> MagicMock:
            return mock_manager

        import sys

        mock_energy_data = MagicMock()
        mock_energy_data.async_get_manager = mock_get_manager
        monkeypatch.setitem(sys.modules, "homeassistant.components.energy.data", mock_energy_data)

        result = await get_energy_entities(hass)

        assert result["grid_import"] == ["sensor.grid_import_1", "sensor.grid_import_2"]
        assert result["grid_export"] == ["sensor.grid_export"]
        assert result["solar"] == ["sensor.solar_east", "sensor.solar_west"]

    @pytest.mark.asyncio
    async def test_raises_when_manager_not_configured(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises ValueError when Energy Dashboard is not configured."""

        async def mock_get_manager(_hass: HomeAssistant) -> None:
            return None

        import sys

        mock_energy_data = MagicMock()
        mock_energy_data.async_get_manager = mock_get_manager
        monkeypatch.setitem(sys.modules, "homeassistant.components.energy.data", mock_energy_data)

        with pytest.raises(ValueError, match="Energy Dashboard not configured"):
            await get_energy_entities(hass)

    @pytest.mark.asyncio
    async def test_raises_when_manager_data_is_none(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises ValueError when Energy Dashboard data is None."""
        mock_manager = MagicMock()
        mock_manager.data = None

        async def mock_get_manager(_hass: HomeAssistant) -> MagicMock:
            return mock_manager

        import sys

        mock_energy_data = MagicMock()
        mock_energy_data.async_get_manager = mock_get_manager
        monkeypatch.setitem(sys.modules, "homeassistant.components.energy.data", mock_energy_data)

        with pytest.raises(ValueError, match="Energy Dashboard not configured"):
            await get_energy_entities(hass)


class TestBuildForecastFromHistory:
    """Tests for build_forecast_from_history function."""

    def test_calculates_total_load_correctly(self) -> None:
        """Total load = grid_import + solar - grid_export."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        hour1 = base_time - timedelta(days=7)
        hour2 = hour1 + timedelta(hours=1)

        statistics: dict[str, list[dict[str, Any]]] = {
            "grid_import": [
                {"start": hour1, "change": 2.0},  # 2 kWh
                {"start": hour2, "change": 3.0},  # 3 kWh
            ],
            "grid_export": [
                {"start": hour1, "change": 0.5},  # 0.5 kWh
                {"start": hour2, "change": 1.0},  # 1 kWh
            ],
            "solar": [
                {"start": hour1, "change": 1.0},  # 1 kWh
                {"start": hour2, "change": 2.0},  # 2 kWh
            ],
        }

        result = build_forecast_from_history(
            statistics=statistics,
            history_days=7,
            current_time=base_time,
        )

        # hour1 shifted forward: 2.0 + 1.0 - 0.5 = 2.5
        # hour2 shifted forward: 3.0 + 2.0 - 1.0 = 4.0
        assert len(result) == 2
        assert result[0][1] == pytest.approx(2.5)
        assert result[1][1] == pytest.approx(4.0)

    def test_returns_empty_when_no_statistics(self) -> None:
        """Returns empty list when no statistics provided."""
        result = build_forecast_from_history(
            statistics={},
            history_days=7,
            current_time=datetime.now(),
        )
        assert result == []

    def test_handles_missing_categories(self) -> None:
        """Works when some categories have no data."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        hour1 = base_time - timedelta(days=7)

        statistics: dict[str, list[dict[str, Any]]] = {
            "grid_import": [
                {"start": hour1, "change": 5.0},
            ],
            "grid_export": [],  # No export
            "solar": [],  # No solar
        }

        result = build_forecast_from_history(
            statistics=statistics,
            history_days=7,
            current_time=base_time,
        )

        # Just grid import: 5.0 + 0 - 0 = 5.0
        assert len(result) == 1
        assert result[0][1] == pytest.approx(5.0)

    def test_clamps_negative_to_zero(self) -> None:
        """Negative total load is clamped to zero."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        hour1 = base_time - timedelta(days=7)

        statistics: dict[str, list[dict[str, Any]]] = {
            "grid_import": [
                {"start": hour1, "change": 1.0},
            ],
            "grid_export": [
                {"start": hour1, "change": 5.0},  # Exporting more than importing
            ],
            "solar": [
                {"start": hour1, "change": 2.0},
            ],
        }

        result = build_forecast_from_history(
            statistics=statistics,
            history_days=7,
            current_time=base_time,
        )

        # 1.0 + 2.0 - 5.0 = -2.0, clamped to 0
        assert len(result) == 1
        assert result[0][1] == pytest.approx(0.0)

    def test_shifts_timestamps_forward(self) -> None:
        """Historical timestamps are shifted forward by history_days."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        historical_hour = base_time - timedelta(days=7)

        statistics: dict[str, list[dict[str, Any]]] = {
            "grid_import": [
                {"start": historical_hour, "change": 1.0},
            ],
            "grid_export": [],
            "solar": [],
        }

        result = build_forecast_from_history(
            statistics=statistics,
            history_days=7,
            current_time=base_time,
        )

        # The timestamp should be shifted to base_time
        expected_timestamp = base_time.timestamp()
        assert result[0][0] == pytest.approx(expected_timestamp)

    def test_filters_past_timestamps(self) -> None:
        """Only includes timestamps in the future relative to current_time."""
        base_time = datetime(2024, 1, 15, 14, 0, 0)
        # This hour, when shifted forward, will be in the past
        past_hour = base_time - timedelta(days=7, hours=3)
        # This hour will be in the future
        future_hour = base_time - timedelta(days=7) + timedelta(hours=1)

        statistics: dict[str, list[dict[str, Any]]] = {
            "grid_import": [
                {"start": past_hour, "change": 1.0},
                {"start": future_hour, "change": 2.0},
            ],
            "grid_export": [],
            "solar": [],
        }

        result = build_forecast_from_history(
            statistics=statistics,
            history_days=7,
            current_time=base_time,
        )

        # Only the future hour should be included
        assert len(result) == 1
        assert result[0][1] == pytest.approx(2.0)


class TestHistoricalLoadLoader:
    """Tests for HistoricalLoadLoader class."""

    def test_default_history_days(self) -> None:
        """Loader uses default history days when not specified."""
        loader = HistoricalLoadLoader()
        assert loader._history_days == DEFAULT_HISTORY_DAYS

    def test_custom_history_days(self) -> None:
        """Loader respects custom history days."""
        loader = HistoricalLoadLoader(history_days=14)
        assert loader._history_days == 14

    def test_available_when_energy_component_loaded(self, hass: HomeAssistant) -> None:
        """available() returns True when energy component is loaded."""
        hass.config.components.add("energy")
        loader = HistoricalLoadLoader()

        assert loader.available(hass=hass)

    def test_not_available_when_energy_component_missing(self, hass: HomeAssistant) -> None:
        """available() returns False when energy component is not loaded."""
        # Create a fresh components set without energy
        original_components = hass.config.components
        hass.config.components = set(c for c in original_components if c != "energy")
        try:
            loader = HistoricalLoadLoader()
            assert not loader.available(hass=hass)
        finally:
            hass.config.components = original_components

    @pytest.mark.asyncio
    async def test_load_returns_empty_for_empty_forecast_times(self, hass: HomeAssistant) -> None:
        """load() returns empty list when forecast_times is empty."""
        loader = HistoricalLoadLoader()

        result = await loader.load(hass=hass, forecast_times=[])

        assert result == []

    @pytest.mark.asyncio
    async def test_load_raises_when_no_grid_import(self, hass: HomeAssistant) -> None:
        """load() raises when no grid import entities are configured."""
        loader = HistoricalLoadLoader()

        mock_entities: EnergyEntities = {
            "grid_import": [],
            "grid_export": [],
            "solar": [],
        }

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_entities",
                new_callable=AsyncMock,
                return_value=mock_entities,
            ),
            pytest.raises(ValueError, match="No grid import entities"),
        ):
            await loader.load(hass=hass, forecast_times=[0.0, 3600.0])

    @pytest.mark.asyncio
    async def test_load_integrates_all_components(self, hass: HomeAssistant) -> None:
        """load() fetches statistics and builds forecast correctly."""
        loader = HistoricalLoadLoader(history_days=7)

        mock_entities: EnergyEntities = {
            "grid_import": ["sensor.grid_import"],
            "grid_export": ["sensor.grid_export"],
            "solar": ["sensor.solar"],
        }

        base_time = datetime(2024, 1, 15, 12, 0, 0)
        hist_hour = base_time - timedelta(days=7)

        # Mock the statistics data
        mock_statistics = {
            "sensor.grid_import": [{"start": hist_hour, "change": 3.0}],
            "sensor.grid_export": [{"start": hist_hour, "change": 1.0}],
            "sensor.solar": [{"start": hist_hour, "change": 2.0}],
        }

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_entities",
                new_callable=AsyncMock,
                return_value=mock_entities,
            ),
            patch(
                "custom_components.haeo.data.loader.historical_load_loader._get_statistics",
                new_callable=AsyncMock,
                return_value=mock_statistics,
            ),
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.dt_util.now",
                return_value=base_time,
            ),
        ):
            # Use forecast times that span the shifted historical data
            forecast_times = [base_time.timestamp(), (base_time + timedelta(hours=1)).timestamp()]
            result = await loader.load(hass=hass, forecast_times=forecast_times)

        # Should return values for each forecast interval
        assert len(result) == 1  # n_periods = len(forecast_times) - 1
        # Value should be: 3.0 + 2.0 - 1.0 = 4.0 kW
        assert result[0] == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_load_raises_when_no_historical_data(self, hass: HomeAssistant) -> None:
        """load() raises when no historical data is available."""
        loader = HistoricalLoadLoader()

        mock_entities: EnergyEntities = {
            "grid_import": ["sensor.grid_import"],
            "grid_export": [],
            "solar": [],
        }

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_entities",
                new_callable=AsyncMock,
                return_value=mock_entities,
            ),
            patch(
                "custom_components.haeo.data.loader.historical_load_loader._get_statistics",
                new_callable=AsyncMock,
                return_value={},  # No statistics
            ),
            pytest.raises(ValueError, match="No historical data available"),
        ):
            await loader.load(hass=hass, forecast_times=[0.0, 3600.0])

    @pytest.mark.asyncio
    async def test_load_aggregates_multiple_entities(self, hass: HomeAssistant) -> None:
        """load() sums values from multiple entities in the same category."""
        loader = HistoricalLoadLoader(history_days=7)

        mock_entities: EnergyEntities = {
            "grid_import": ["sensor.grid_import_1", "sensor.grid_import_2"],
            "grid_export": [],
            "solar": [],
        }

        base_time = datetime(2024, 1, 15, 12, 0, 0)
        hist_hour = base_time - timedelta(days=7)

        # Two grid import sensors with values that should be summed
        mock_statistics = {
            "sensor.grid_import_1": [{"start": hist_hour, "change": 2.0}],
            "sensor.grid_import_2": [{"start": hist_hour, "change": 3.0}],
        }

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_entities",
                new_callable=AsyncMock,
                return_value=mock_entities,
            ),
            patch(
                "custom_components.haeo.data.loader.historical_load_loader._get_statistics",
                new_callable=AsyncMock,
                return_value=mock_statistics,
            ),
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.dt_util.now",
                return_value=base_time,
            ),
        ):
            forecast_times = [base_time.timestamp(), (base_time + timedelta(hours=1)).timestamp()]
            result = await loader.load(hass=hass, forecast_times=forecast_times)

        # Should sum the two import values: 2.0 + 3.0 = 5.0 kW
        assert len(result) == 1
        assert result[0] == pytest.approx(5.0)
