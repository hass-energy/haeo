"""Tests for data extractor functionality."""

from typing import Any

from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.haeo.core.data.loader import extractors
from custom_components.haeo.core.data.loader.extractors.tests.test_data.sensors import (
    ALL_INVALID_SENSORS,
    ALL_VALID_SENSORS,
)


def _create_sensor_state(hass: HomeAssistant, entity_id: str, state_value: str, attributes: dict[str, Any]) -> State:
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
def test_extract_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test extraction of valid forecast data."""
    state = _create_sensor_state(hass, sensor_data["entity_id"], sensor_data["state"], sensor_data["attributes"])

    result = extractors.extract(state)

    assert result is not None, f"Expected data for {parser_type}"
    assert isinstance(result.data, list), "Valid forecasts should return a list of time series entries"

    expected_data: list[tuple[float, float]] = sensor_data["expected_data"]
    assert len(result.data) == len(expected_data)
    for actual, expected in zip(result.data, expected_data, strict=True):
        assert actual == pytest.approx(expected, rel=1e-9)

    expected_unit: str = sensor_data["expected_unit"]
    assert result.unit == expected_unit


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_INVALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_invalid_sensor_handling(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test handling of invalid sensor data."""
    entity_id = sensor_data["entity_id"]
    state = _create_sensor_state(hass, entity_id, sensor_data["state"], sensor_data["attributes"])

    # Invalid sensors should fall back to simple value extraction
    result = extractors.extract(state)

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
    ],
)
def test_extract_unknown_format_fallback(
    hass: HomeAssistant,
    state_value: str,
    attributes: dict[str, Any],
    expected_value: float,
    expected_unit: str | None,
) -> None:
    """Unknown attributes fall back to simple value extraction."""
    state = _create_sensor_state(hass, "sensor.unknown", state_value, attributes)

    result = extractors.extract(state)

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
        extractors.extract(state)


PARSER_MAP: dict[str, extractors.DataExtractor] = {
    extractors.amber2mqtt.DOMAIN: extractors.amber2mqtt.Parser,
    extractors.amberelectric.DOMAIN: extractors.amberelectric.Parser,
    extractors.aemo_nem.DOMAIN: extractors.aemo_nem.Parser,
    extractors.flow_power.DOMAIN: extractors.flow_power.Parser,
    extractors.haeo.DOMAIN: extractors.haeo.Parser,
    extractors.solcast_solar.DOMAIN: extractors.solcast_solar.Parser,
    extractors.open_meteo_solar_forecast.DOMAIN: extractors.open_meteo_solar_forecast.Parser,
}


# --- Interpolation Mode Tests ---


class TestInterpolationModeExtraction:
    """Tests for interpolation_mode attribute extraction."""

    @pytest.mark.parametrize(
        "interpolation_mode",
        [None, "linear"],
        ids=["default_linear", "explicit_linear"],
    )
    def test_linear_modes_leave_data_unchanged(self, hass: HomeAssistant, interpolation_mode: str | None) -> None:
        """Missing or explicit linear interpolation leaves data unchanged."""
        attributes: dict[str, Any] = {
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

        result = extractors.extract(state)
        assert isinstance(result.data, list)
        assert len(result.data) == 2

    def test_previous_mode_adds_synthetic_points(self, hass: HomeAssistant) -> None:
        """Previous mode adds synthetic points for step function behavior."""
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

        result = extractors.extract(state)
        assert isinstance(result.data, list)
        # Previous mode: 2 original + 1 synthetic = 3 points
        assert len(result.data) == 3
        # First point unchanged
        assert result.data[0][1] == 100.0
        # Synthetic point just before second with previous value
        assert result.data[1][1] == 100.0
        # Second point
        assert result.data[2][1] == 200.0

    def test_next_mode_adds_synthetic_points(self, hass: HomeAssistant) -> None:
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

        result = extractors.extract(state)
        assert isinstance(result.data, list)
        # Next mode: 2 original + 1 synthetic = 3 points
        assert len(result.data) == 3
        # First point unchanged
        assert result.data[0][1] == 100.0
        # Synthetic point just after first with next value
        assert result.data[1][1] == 200.0
        # Second point
        assert result.data[2][1] == 200.0

    def test_nearest_mode_adds_synthetic_points(self, hass: HomeAssistant) -> None:
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

        result = extractors.extract(state)
        assert isinstance(result.data, list)
        # Nearest mode: 2 original + 2 synthetic = 4 points
        assert len(result.data) == 4

    def test_invalid_mode_falls_back_to_linear(self, hass: HomeAssistant) -> None:
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

        result = extractors.extract(state)
        assert isinstance(result.data, list)
        # Falls back to linear: only 2 points
        assert len(result.data) == 2

    def test_simple_value_ignores_interpolation_mode(self, hass: HomeAssistant) -> None:
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

        result = extractors.extract(state)
        # Simple value extraction, not affected by interpolation_mode
        assert isinstance(result.data, float)
        assert result.data == 42.0
