"""Tests for the historical load loader."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader.historical_load_loader import (
    EnergyEntities,
    HistoricalLoadLoader,
    build_forecast_from_history,
    get_energy_entities,
)


class TestEnergyEntities:
    """Tests for EnergyEntities class."""

    def test_all_entity_ids_returns_all_entities(self) -> None:
        """Should return all entity IDs from all categories."""
        entities = EnergyEntities(
            grid_import=["sensor.import"],
            grid_export=["sensor.export"],
            solar=["sensor.solar"],
        )
        assert entities.all_entity_ids() == ["sensor.import", "sensor.export", "sensor.solar"]

    def test_has_entities_returns_true_when_entities_exist(self) -> None:
        """Should return True when any entities are configured."""
        assert EnergyEntities(grid_import=["sensor.import"]).has_entities() is True
        assert EnergyEntities(grid_export=["sensor.export"]).has_entities() is True
        assert EnergyEntities(solar=["sensor.solar"]).has_entities() is True

    def test_has_entities_returns_false_when_empty(self) -> None:
        """Should return False when no entities are configured."""
        assert EnergyEntities().has_entities() is False


class TestGetEnergyEntities:
    """Tests for get_energy_entities function."""

    @pytest.mark.asyncio
    async def test_returns_categorized_entities_from_energy_manager(self, hass: HomeAssistant) -> None:
        """Should return categorized entities from the Energy Manager."""
        mock_manager = MagicMock()
        mock_manager.data = {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {"stat_energy_from": "sensor.grid_import"},
                        {"stat_energy_from": "sensor.grid_import_2"},
                    ],
                    "flow_to": [
                        {"stat_energy_to": "sensor.grid_export"},
                    ],
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
            result = await get_energy_entities(hass)

        assert result.grid_import == ["sensor.grid_import", "sensor.grid_import_2"]
        assert result.grid_export == ["sensor.grid_export"]
        assert result.solar == ["sensor.solar_production"]

    @pytest.mark.asyncio
    async def test_returns_empty_entities_when_no_energy_sources(self, hass: HomeAssistant) -> None:
        """Should return empty EnergyEntities when no energy sources are configured."""
        mock_manager = MagicMock()
        mock_manager.data = {"energy_sources": []}

        with patch(
            "homeassistant.components.energy.data.async_get_manager",
            new=AsyncMock(return_value=mock_manager),
        ):
            result = await get_energy_entities(hass)

        assert result.grid_import == []
        assert result.grid_export == []
        assert result.solar == []
        assert result.has_entities() is False

    @pytest.mark.asyncio
    async def test_returns_empty_entities_when_manager_has_no_data(self, hass: HomeAssistant) -> None:
        """Should return empty EnergyEntities when manager has no data."""
        mock_manager = MagicMock()
        mock_manager.data = None

        with patch(
            "homeassistant.components.energy.data.async_get_manager",
            new=AsyncMock(return_value=mock_manager),
        ):
            result = await get_energy_entities(hass)

        assert result.has_entities() is False

    @pytest.mark.asyncio
    async def test_handles_multiple_solar_sources(self, hass: HomeAssistant) -> None:
        """Should handle multiple solar sources."""
        mock_manager = MagicMock()
        mock_manager.data = {
            "energy_sources": [
                {
                    "type": "solar",
                    "stat_energy_from": "sensor.solar_roof",
                },
                {
                    "type": "solar",
                    "stat_energy_from": "sensor.solar_carport",
                },
            ]
        }

        with patch(
            "homeassistant.components.energy.data.async_get_manager",
            new=AsyncMock(return_value=mock_manager),
        ):
            result = await get_energy_entities(hass)

        assert result.solar == ["sensor.solar_roof", "sensor.solar_carport"]


class TestBuildForecastFromHistory:
    """Tests for build_forecast_from_history function."""

    def test_builds_forecast_from_grid_import_only(self) -> None:
        """Should build a forecast from grid import data alone."""
        now = datetime.now(tz=UTC)
        hour_1 = now - timedelta(hours=2)
        hour_2 = now - timedelta(hours=1)

        statistics: Any = {
            "sensor.grid_import": [
                {"start": hour_1, "change": 1.5},
                {"start": hour_2, "change": 2.0},
            ]
        }
        energy_entities = EnergyEntities(grid_import=["sensor.grid_import"])

        result = build_forecast_from_history(statistics, energy_entities, history_days=7)

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

    def test_calculates_total_load_from_all_sources(self) -> None:
        """Should calculate total load as: grid_import + solar - grid_export."""
        now = datetime.now(tz=UTC)
        hour_1 = now - timedelta(hours=1)

        # Scenario: 2 kWh import, 3 kWh solar, 1 kWh export
        # Total load = 2 + 3 - 1 = 4 kWh
        statistics: Any = {
            "sensor.grid_import": [{"start": hour_1, "change": 2.0}],
            "sensor.solar": [{"start": hour_1, "change": 3.0}],
            "sensor.grid_export": [{"start": hour_1, "change": 1.0}],
        }
        energy_entities = EnergyEntities(
            grid_import=["sensor.grid_import"],
            grid_export=["sensor.grid_export"],
            solar=["sensor.solar"],
        )

        result = build_forecast_from_history(statistics, energy_entities, history_days=7)

        assert len(result) == 1
        assert result[0][1] == 4.0  # 2 + 3 - 1

    def test_handles_solar_self_consumption(self) -> None:
        """Should correctly calculate load when solar covers all consumption."""
        now = datetime.now(tz=UTC)
        hour_1 = now - timedelta(hours=1)

        # Scenario: 0 kWh import (solar covers everything), 5 kWh solar, 3 kWh export
        # Total load = 0 + 5 - 3 = 2 kWh (self-consumed)
        statistics: Any = {
            "sensor.grid_import": [{"start": hour_1, "change": 0.0}],
            "sensor.solar": [{"start": hour_1, "change": 5.0}],
            "sensor.grid_export": [{"start": hour_1, "change": 3.0}],
        }
        energy_entities = EnergyEntities(
            grid_import=["sensor.grid_import"],
            grid_export=["sensor.grid_export"],
            solar=["sensor.solar"],
        )

        result = build_forecast_from_history(statistics, energy_entities, history_days=7)

        assert len(result) == 1
        assert result[0][1] == 2.0

    def test_sums_multiple_entities_per_category(self) -> None:
        """Should sum values from multiple entities in the same category."""
        now = datetime.now(tz=UTC)
        hour_1 = now - timedelta(hours=1)

        # Two grid import sensors, two solar panels
        statistics: Any = {
            "sensor.grid_import_1": [{"start": hour_1, "change": 1.0}],
            "sensor.grid_import_2": [{"start": hour_1, "change": 0.5}],
            "sensor.solar_roof": [{"start": hour_1, "change": 2.0}],
            "sensor.solar_carport": [{"start": hour_1, "change": 1.0}],
            "sensor.grid_export": [{"start": hour_1, "change": 0.5}],
        }
        energy_entities = EnergyEntities(
            grid_import=["sensor.grid_import_1", "sensor.grid_import_2"],
            grid_export=["sensor.grid_export"],
            solar=["sensor.solar_roof", "sensor.solar_carport"],
        )

        result = build_forecast_from_history(statistics, energy_entities, history_days=7)

        # Total = (1.0 + 0.5) + (2.0 + 1.0) - 0.5 = 4.0
        assert len(result) == 1
        assert result[0][1] == 4.0

    def test_returns_empty_list_for_empty_statistics(self) -> None:
        """Should return empty list when no statistics are provided."""
        energy_entities = EnergyEntities(grid_import=["sensor.import"])
        result = build_forecast_from_history({}, energy_entities, history_days=7)
        assert result == []

    def test_skips_entries_without_change(self) -> None:
        """Should skip entries without a change value."""
        now = datetime.now(tz=UTC)

        statistics: Any = {
            "sensor.grid_import": [
                {"start": now - timedelta(hours=2), "change": 1.0},
                {"start": now - timedelta(hours=1), "change": None},
            ]
        }
        energy_entities = EnergyEntities(grid_import=["sensor.grid_import"])

        result = build_forecast_from_history(statistics, energy_entities, history_days=7)

        assert len(result) == 1
        assert result[0][1] == 1.0

    def test_ensures_non_negative_total_load(self) -> None:
        """Should ensure total load is never negative."""
        now = datetime.now(tz=UTC)
        hour_1 = now - timedelta(hours=1)

        # Edge case: more export than import+solar (shouldn't happen, but protect against it)
        statistics: Any = {
            "sensor.grid_import": [{"start": hour_1, "change": 1.0}],
            "sensor.grid_export": [{"start": hour_1, "change": 5.0}],
        }
        energy_entities = EnergyEntities(
            grid_import=["sensor.grid_import"],
            grid_export=["sensor.grid_export"],
        )

        result = build_forecast_from_history(statistics, energy_entities, history_days=7)

        assert len(result) == 1
        assert result[0][1] == 0.0  # Clamped to 0


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
    async def test_load_raises_when_no_energy_entities(self, hass: HomeAssistant) -> None:
        """Should raise ValueError when no energy entities are configured."""
        loader = HistoricalLoadLoader()

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_entities",
                new=AsyncMock(return_value=EnergyEntities()),
            ),
            pytest.raises(ValueError, match="No energy sensors configured"),
        ):
            await loader.load(hass=hass, value=7, forecast_times=[0, 3600, 7200])

    @pytest.mark.asyncio
    async def test_load_raises_when_no_historical_data(self, hass: HomeAssistant) -> None:
        """Should raise ValueError when no historical data is available."""
        loader = HistoricalLoadLoader()

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_entities",
                new=AsyncMock(return_value=EnergyEntities(grid_import=["sensor.import"])),
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

        # Create mock historical data with grid import and solar
        now = datetime.now(tz=UTC)
        statistics = {
            "sensor.grid_import": [
                {"start": now - timedelta(hours=2), "change": 1.0},
                {"start": now - timedelta(hours=1), "change": 2.0},
            ],
            "sensor.solar": [
                {"start": now - timedelta(hours=2), "change": 0.5},
                {"start": now - timedelta(hours=1), "change": 1.0},
            ],
        }
        energy_entities = EnergyEntities(
            grid_import=["sensor.grid_import"],
            solar=["sensor.solar"],
        )

        with (
            patch(
                "custom_components.haeo.data.loader.historical_load_loader.get_energy_entities",
                new=AsyncMock(return_value=energy_entities),
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
