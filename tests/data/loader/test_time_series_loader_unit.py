"""Unit tests for time series loader's entity ID handling and error cases.

Integration tests with Home Assistant state are in test_time_series_loader.py.
Lower-level fusion and cycling logic is tested in:
- tests/data/util/test_forecast_fuser.py (fusion logic)
- tests/data/util/test_forecast_cycle.py (cycling logic)
- tests/data/util/test_forecast_combiner.py (combining logic)
"""

from collections.abc import Sequence
from typing import Any

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import historical_load_loader as hll
from custom_components.haeo.data.loader import time_series_loader as tsl
from custom_components.haeo.data.loader.sensor_loader import normalize_entity_ids
from custom_components.haeo.data.loader.time_series_loader import TimeSeriesLoader, _collect_sensor_ids


def test_collect_sensor_ids_from_mapping() -> None:
    """Ensure mapping inputs expand into a flattened sensor list."""

    value = {
        "present": "sensor.present_power",
        "forecast": ("sensor.forecast_day", "sensor.forecast_night"),
        "optional": None,
    }

    assert _collect_sensor_ids(value) == [
        "sensor.present_power",
        "sensor.forecast_day",
        "sensor.forecast_night",
    ]


def test_normalize_entity_ids_rejects_invalid_type() -> None:
    """normalize_entity_ids should reject non-string, non-sequence inputs."""

    with pytest.raises(TypeError):
        normalize_entity_ids(123)


def test_time_series_loader_available_counts_every_sensor(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """available() should succeed when all referenced sensors load correctly."""

    loader = TimeSeriesLoader()
    captured: list[str] = []

    def fake_load_sensors(_hass: HomeAssistant, entity_ids: Sequence[str]) -> dict[str, float]:
        captured.extend(entity_ids)
        return dict.fromkeys(entity_ids, 0.0)

    monkeypatch.setattr(tsl, "load_sensors", fake_load_sensors)

    value = {
        "present": "sensor.present_power",
        "forecast": ("sensor.forecast_day",),
        "ignored": None,
    }

    assert loader.available(hass=hass, value=value)
    assert captured == ["sensor.present_power", "sensor.forecast_day"]


def test_time_series_loader_available_missing_payloads(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """available() should return False when any referenced sensor fails to load."""

    loader = TimeSeriesLoader()

    def fake_load_sensors(_hass: HomeAssistant, entity_ids: Sequence[str]) -> dict[str, float]:
        return {entity_ids[0]: 0.0}

    monkeypatch.setattr(tsl, "load_sensors", fake_load_sensors)

    assert not loader.available(hass=hass, value=["sensor.one", "sensor.two"])


def test_time_series_loader_available_invalid_value(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """available() should gracefully reject invalid value types."""

    loader = TimeSeriesLoader()

    def fail_load_sensors(_hass: HomeAssistant, _entity_ids: Sequence[str]) -> None:
        pytest.fail("load_sensors should not be called for invalid inputs")

    monkeypatch.setattr(tsl, "load_sensors", fail_load_sensors)

    assert not loader.available(hass=hass, value=object())


@pytest.mark.asyncio
async def test_time_series_loader_load_merges_present_and_forecast(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load() should merge present and forecast values into the target horizon."""

    loader = TimeSeriesLoader()

    def fake_load_sensors(_hass: HomeAssistant, entity_ids: Sequence[str]) -> dict[str, object]:
        assert list(entity_ids) == [
            "sensor.present_power",
            "sensor.forecast_day",
            "sensor.forecast_night",
        ]
        return {
            "sensor.present_power": 1.5,
            "sensor.forecast_day": [(150, 2.0), (300, 4.0)],
            "sensor.forecast_night": [(150, 1.0), (450, 3.0)],
        }

    monkeypatch.setattr(tsl, "load_sensors", fake_load_sensors)

    result = await loader.load(
        hass=hass,
        value=["sensor.present_power", "sensor.forecast_day", "sensor.forecast_night"],
        forecast_times=[100, 250, 400, 700, 850],
    )

    # Verify correct number of interval values
    assert len(result) == 4
    assert result[0] == pytest.approx(1.5)
    # Remaining values are computed by fusion logic (tested in test_forecast_fuser.py)
    assert all(isinstance(v, float) for v in result)


@pytest.mark.asyncio
async def test_time_series_loader_load_present_only_uses_historical(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load() should use historical data when sensors have no forecasts."""

    loader = TimeSeriesLoader()

    def fake_load_sensors(_hass: HomeAssistant, entity_ids: Sequence[str]) -> dict[str, float]:
        assert list(entity_ids) == ["sensor.a", "sensor.b"]
        return {"sensor.a": 2.0, "sensor.b": 3.0}

    monkeypatch.setattr(tsl, "load_sensors", fake_load_sensors)

    # Mock the HistoricalForecastLoader to return a ForecastSeries
    # TimeSeriesLoader._load_from_history will pass this to fuse_to_horizon
    async def fake_historical_load(
        self: Any,
        *,
        hass: HomeAssistant,
        value: list[str],
        forecast_times: Sequence[float],
        **_kwargs: Any,
    ) -> list[tuple[float, float]]:
        # Return ForecastSeries with values at forecast_times
        return [(0, 4.0), (60, 6.0), (120, 8.0)]

    monkeypatch.setattr(hll.HistoricalForecastLoader, "load", fake_historical_load)

    result = await loader.load(
        hass=hass,
        value=["sensor.a", "sensor.b"],
        forecast_times=[0, 60, 120],
    )

    # Returns values fused from the ForecastSeries (n-1 intervals)
    # Note: fuse_to_horizon replaces interval 0 with present_value (2.0 + 3.0 = 5.0)
    # and uses forecast data for subsequent intervals via trapezoidal integration
    assert len(result) == 2
    assert result[0] == pytest.approx(5.0)  # Present value (summed sensors)
    assert result[1] == pytest.approx(7.0)  # Average of 6.0 and 8.0 (trapezoidal)


@pytest.mark.asyncio
async def test_time_series_loader_load_present_only_fallback(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load() should fallback to present value when historical data fails."""

    loader = TimeSeriesLoader()

    def fake_load_sensors(_hass: HomeAssistant, entity_ids: Sequence[str]) -> dict[str, float]:
        return {"sensor.a": 2.0, "sensor.b": 3.0}

    monkeypatch.setattr(tsl, "load_sensors", fake_load_sensors)

    # Mock the HistoricalForecastLoader to fail
    async def fake_historical_load(
        self: Any, **_kwargs: Any
    ) -> list[tuple[float, float]]:
        msg = "No historical data available"
        raise ValueError(msg)

    monkeypatch.setattr(hll.HistoricalForecastLoader, "load", fake_historical_load)

    result = await loader.load(
        hass=hass,
        value=["sensor.a", "sensor.b"],
        forecast_times=[0, 60, 120],
    )

    # Falls back to summed present value broadcast: 2.0 + 3.0 = 5.0
    assert result == [5.0, 5.0]


@pytest.mark.asyncio
async def test_time_series_loader_load_returns_empty_for_missing_horizon(hass: HomeAssistant) -> None:
    """load() should return an empty series when forecast_times is empty."""

    loader = TimeSeriesLoader()

    result = await loader.load(
        hass=hass,
        value="sensor.any",
        forecast_times=[],
    )

    assert result == []


@pytest.mark.asyncio
async def test_time_series_loader_load_requires_entity_ids(hass: HomeAssistant) -> None:
    """load() should reject configurations without sensor references."""

    loader = TimeSeriesLoader()

    with pytest.raises(ValueError, match="At least one sensor entity is required"):
        await loader.load(
            hass=hass,
            value=(),
            forecast_times=[0, 60],
        )


@pytest.mark.asyncio
async def test_time_series_loader_load_fails_when_no_payloads(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load() should raise when no sensor provided usable data."""

    loader = TimeSeriesLoader()

    def fake_load_sensors(_hass: HomeAssistant, _entity_ids: Sequence[str]) -> dict[str, float]:
        return {}

    monkeypatch.setattr(tsl, "load_sensors", fake_load_sensors)

    with pytest.raises(ValueError, match="No time series data available"):
        await loader.load(
            hass=hass,
            value=["sensor.present", "sensor.forecast"],
            forecast_times=[0, 60],
        )


@pytest.mark.asyncio
async def test_time_series_loader_load_fails_when_sensor_missing(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load() should raise when at least one referenced sensor failed to load."""

    loader = TimeSeriesLoader()

    def fake_load_sensors(_hass: HomeAssistant, entity_ids: Sequence[str]) -> dict[str, float]:
        return {entity_ids[0]: 0.0}

    monkeypatch.setattr(tsl, "load_sensors", fake_load_sensors)

    with pytest.raises(ValueError, match=r"sensor\.missing"):
        await loader.load(
            hass=hass,
            value=["sensor.present", "sensor.missing"],
            forecast_times=[0, 60],
        )
