"""Tests for data extractor functionality."""

from datetime import UTC, datetime

from homeassistant.core import HomeAssistant, State
import numpy as np
import pytest

from conftest import FakeEntityState
from custom_components.haeo.core.data.loader import extractors
from custom_components.haeo.core.data.loader.extractors import emhass
from custom_components.haeo.core.data.loader.extractors.tests.test_data.sensors import (
    ALL_INVALID_SENSORS,
    ALL_VALID_SENSORS,
)
from custom_components.haeo.core.data.util.forecast_fuser import fuse_to_intervals


def _create_sensor_state(hass: HomeAssistant, entity_id: str, state_value: str, attributes: dict[str, object]) -> State:
    """Create a sensor state and return it.

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to create
        state_value: State value to set
        attributes: State attributes to set

    Returns:
        The created state object

    """
    hass.states.async_set(entity_id, state_value, attributes)

    if (state := hass.states.get(entity_id)) is None:
        msg = f"Failed to get state for {entity_id}"
        raise RuntimeError(msg)
    return state


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_VALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_extract_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, object]) -> None:
    """Test extraction of valid forecast data."""
    entity_id = sensor_data["entity_id"]
    state_value = sensor_data["state"]
    attributes = sensor_data["attributes"]
    assert isinstance(entity_id, str)
    assert isinstance(state_value, str)
    assert isinstance(attributes, dict)
    state = _create_sensor_state(hass, entity_id, state_value, attributes)

    result = extractors.extract(state, time_zone=UTC)

    assert result is not None, f"Expected data for {parser_type}"
    assert isinstance(result.data, list), "Valid forecasts should return a list of time series entries"

    expected_data = sensor_data["expected_data"]
    assert isinstance(expected_data, list)
    assert len(result.data) == len(expected_data)
    for actual, expected in zip(result.data, expected_data, strict=True):
        assert actual == pytest.approx(expected, rel=1e-9)

    expected_unit = sensor_data["expected_unit"]
    assert isinstance(expected_unit, str)
    assert result.unit == expected_unit


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_INVALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_invalid_sensor_handling(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, object]) -> None:
    """Test handling of invalid sensor data."""
    entity_id = sensor_data["entity_id"]
    state_value = sensor_data["state"]
    attributes = sensor_data["attributes"]
    assert isinstance(entity_id, str)
    assert isinstance(state_value, str)
    assert isinstance(attributes, dict)
    state = _create_sensor_state(hass, entity_id, state_value, attributes)

    # Invalid sensors should fall back to simple value extraction
    result = extractors.extract(state, time_zone=UTC)

    # Should fall back to reading the state as a float
    assert isinstance(result.data, float)


@pytest.mark.parametrize(
    ("state_value", "attributes", "expected_value", "expected_unit"),
    [
        pytest.param("42.0", {}, 42.0, None, id="empty_attributes"),
        pytest.param("42.5", {"unknown_field": "value"}, 42.5, None, id="unknown_attributes"),
        pytest.param(
            "42.0",
            {"unit_of_measurement": "test_unit"},
            42.0,
            "test_unit",
            id="unknown_with_unit",
        ),
        pytest.param(
            "16.3",
            {"unit_of_measurement": "kWh/100 km"},
            pytest.approx(0.163),
            "kWh/km",
            id="unit_with_spaces",
        ),
        pytest.param("on", {}, 1.0, None, id="binary_on"),
        pytest.param("off", {}, 0.0, None, id="binary_off"),
        pytest.param("true", {}, 1.0, None, id="binary_true"),
        pytest.param("false", {}, 0.0, None, id="binary_false"),
        pytest.param("ON", {}, 1.0, None, id="binary_uppercase"),
        pytest.param(" Off ", {}, 0.0, None, id="binary_mixed_case_whitespace"),
    ],
)
def test_extract_unknown_format_fallback(
    hass: HomeAssistant,
    state_value: str,
    attributes: dict[str, object],
    expected_value: float,
    expected_unit: str | None,
) -> None:
    """Unknown attributes fall back to simple value extraction."""
    state = _create_sensor_state(hass, "sensor.unknown", state_value, attributes)

    result = extractors.extract(state, time_zone=UTC)

    assert isinstance(result.data, float)
    assert result.data == expected_value
    assert result.unit == expected_unit


def test_extract_raises_for_non_numeric_state(hass: HomeAssistant) -> None:
    """Simple value extraction should raise when the sensor state is not numeric."""

    entity_id = "sensor.invalid_numeric"
    state = _create_sensor_state(
        hass,
        entity_id,
        "not-a-number",
        {"unit_of_measurement": "kWh"},
    )

    with pytest.raises(ValueError, match="could not convert string to float"):
        extractors.extract(state, time_zone=UTC)


def test_extract_raises_for_zero_in_a_reciprocal_unit(hass: HomeAssistant) -> None:
    """Zero km/kWh is not a reading, as it has no finite energy per distance."""
    state = _create_sensor_state(hass, "sensor.efficiency", "0", {"unit_of_measurement": "km/kWh"})

    with pytest.raises(ValueError, match="reciprocal"):
        extractors.extract(state, time_zone=UTC)


def test_aemo_block_prices_fuse_to_steps(hass: HomeAssistant) -> None:
    """AEMO block prices hold for their whole block instead of ramping into the next one."""
    blocks = [
        ("2025-10-05T21:00:00+10:00", "2025-10-05T21:30:00+10:00", 0.0),
        ("2025-10-05T21:30:00+10:00", "2025-10-05T22:00:00+10:00", 0.0),
        ("2025-10-05T22:00:00+10:00", "2025-10-05T22:30:00+10:00", 0.5),
        ("2025-10-05T22:30:00+10:00", "2025-10-05T23:00:00+10:00", 0.5),
    ]
    state = _create_sensor_state(
        hass,
        "sensor.aemo_forecast",
        "0.0",
        {"forecast": [{"start_time": start, "end_time": end, "price": price} for start, end, price in blocks]},
    )

    result = extractors.extract(state, time_zone=UTC)
    assert isinstance(result.data, list)
    start = 1759662000
    horizon_times = [start + 1800 * period for period in range(5)]

    assert fuse_to_intervals(None, result.data, horizon_times) == pytest.approx([0.0, 0.0, 0.5, 0.5], abs=1e-9)


def test_solcast_period_means_of_a_ramp_fuse_back_to_the_same_means(hass: HomeAssistant) -> None:
    """Solcast means sit at the middle of their periods, so a linear ramp fuses back to its period means."""
    start = 1759662000
    means = [1.0, 2.0, 3.0, 4.0]
    state = _create_sensor_state(
        hass,
        "sensor.solcast_forecast",
        "1.0",
        {
            "detailedForecast": [
                {"period_start": datetime.fromtimestamp(start + 1800 * period, tz=UTC), "pv_estimate": mean}
                for period, mean in enumerate(means)
            ]
        },
    )

    result = extractors.extract(state, time_zone=UTC)
    assert isinstance(result.data, list)
    horizon_times = [start + 1800 * period for period in range(len(means) + 1)]

    # The first and last periods are only half covered by the ramp, so only the inner periods are exact
    assert fuse_to_intervals(None, result.data, horizon_times)[1:-1] == pytest.approx(means[1:-1])


def test_haeo_interval_forecast_fuses_to_its_period_values(hass: HomeAssistant) -> None:
    """A HAEO interval forecast read back by another input keeps each period's value, including the last."""
    start = 1759662000
    values = [1.0, 3.0, 2.0]
    state = _create_sensor_state(
        hass,
        "sensor.haeo_battery_power",
        "1.0",
        {
            "forecast": [
                {"time": datetime.fromtimestamp(start + 1800 * period, tz=UTC), "value": value}
                for period, value in enumerate(values)
            ],
            "unit_of_measurement": "kW",
            "interpolation_mode": "previous",
        },
    )

    result = extractors.extract(state, time_zone=UTC)
    assert isinstance(result.data, list)
    horizon_times = [start + 1800 * period for period in range(len(values) + 1)]

    assert fuse_to_intervals(None, result.data, horizon_times) == pytest.approx(values, abs=1e-9)


# --- Interpolation Mode Tests ---


@pytest.mark.parametrize(
    "interpolation_mode",
    [None, "linear"],
    ids=["default_linear", "explicit_linear"],
)
def test_linear_modes_leave_data_unchanged(hass: HomeAssistant, interpolation_mode: str | None) -> None:
    """Missing or explicit linear interpolation leaves data unchanged."""
    attributes: dict[str, object] = {
        "forecast": [
            {"time": "2024-01-01T00:00:00+00:00", "value": 100.0},
            {"time": "2024-01-01T01:00:00+00:00", "value": 200.0},
        ],
        "unit_of_measurement": "kW",
    }
    if interpolation_mode is not None:
        attributes["interpolation_mode"] = interpolation_mode

    state = _create_sensor_state(
        hass,
        "sensor.haeo_forecast",
        "100.0",
        attributes,
    )

    result = extractors.extract(state, time_zone=UTC)
    assert isinstance(result.data, list)
    assert len(result.data) == 2


def test_previous_mode_holds_each_value_until_the_next(hass: HomeAssistant) -> None:
    """Previous mode holds each value until the next point, and the last for one more step."""
    state = _create_sensor_state(
        hass,
        "sensor.haeo_forecast",
        "100.0",
        {
            "forecast": [
                {"time": "2024-01-01T00:00:00+00:00", "value": 100.0},
                {"time": "2024-01-01T01:00:00+00:00", "value": 200.0},
            ],
            "unit_of_measurement": "kW",
            "interpolation_mode": "previous",
        },
    )

    result = extractors.extract(state, time_zone=UTC)
    assert result.data == [
        (1704067200.0, 100.0),
        (np.nextafter(1704070800.0, -np.inf), 100.0),
        (1704070800.0, 200.0),
        (1704074400.0, 200.0),
    ]


def test_next_mode_adds_synthetic_points(hass: HomeAssistant) -> None:
    """Next mode adds synthetic points for forward step behavior."""
    state = _create_sensor_state(
        hass,
        "sensor.haeo_forecast",
        "100.0",
        {
            "forecast": [
                {"time": "2024-01-01T00:00:00+00:00", "value": 100.0},
                {"time": "2024-01-01T01:00:00+00:00", "value": 200.0},
            ],
            "unit_of_measurement": "kW",
            "interpolation_mode": "next",
        },
    )

    result = extractors.extract(state, time_zone=UTC)
    assert isinstance(result.data, list)
    # Next mode: 2 original + 1 synthetic = 3 points
    assert len(result.data) == 3
    # First point unchanged
    assert result.data[0][1] == 100.0
    # Synthetic point just after first with next value
    assert result.data[1][1] == 200.0
    # Second point
    assert result.data[2][1] == 200.0


def test_nearest_mode_adds_synthetic_points(hass: HomeAssistant) -> None:
    """Nearest mode adds synthetic points at midpoints."""
    state = _create_sensor_state(
        hass,
        "sensor.haeo_forecast",
        "100.0",
        {
            "forecast": [
                {"time": "2024-01-01T00:00:00+00:00", "value": 100.0},
                {"time": "2024-01-01T01:00:00+00:00", "value": 200.0},
            ],
            "unit_of_measurement": "kW",
            "interpolation_mode": "nearest",
        },
    )

    result = extractors.extract(state, time_zone=UTC)
    assert isinstance(result.data, list)
    # Nearest mode: 2 original + 2 synthetic = 4 points
    assert len(result.data) == 4


def test_invalid_mode_falls_back_to_linear(hass: HomeAssistant) -> None:
    """Invalid interpolation_mode value falls back to linear."""
    state = _create_sensor_state(
        hass,
        "sensor.haeo_forecast",
        "100.0",
        {
            "forecast": [
                {"time": "2024-01-01T00:00:00+00:00", "value": 100.0},
                {"time": "2024-01-01T01:00:00+00:00", "value": 200.0},
            ],
            "unit_of_measurement": "kW",
            "interpolation_mode": "invalid_mode",
        },
    )

    result = extractors.extract(state, time_zone=UTC)
    assert isinstance(result.data, list)
    # Falls back to linear: only 2 points
    assert len(result.data) == 2


def test_simple_value_ignores_interpolation_mode(hass: HomeAssistant) -> None:
    """Interpolation mode is ignored for simple (non-forecast) values."""
    state = _create_sensor_state(
        hass,
        "sensor.simple",
        "42.0",
        {
            "unit_of_measurement": "kW",
            "interpolation_mode": "previous",
        },
    )

    result = extractors.extract(state, time_zone=UTC)
    # Simple value extraction, not affected by interpolation_mode
    assert isinstance(result.data, float)
    assert result.data == 42.0


def test_emhass_extract_without_a_forecast_raises() -> None:
    """Extracting EMHASS data from a state without a forecast fails loudly rather than reading nothing."""
    state = FakeEntityState("sensor.p_load_forecast", "1", {"forecasts": []})

    with pytest.raises(ValueError, match="no EMHASS forecast"):
        emhass.Parser.extract(state, UTC)  # type: ignore[arg-type]  # a state detect() rejects, which extract() must refuse
