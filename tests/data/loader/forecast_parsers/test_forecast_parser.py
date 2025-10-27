"""Tests for forecast parser functionality."""

from typing import Any

from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.haeo.data.loader.forecast_parsers import detect_format, get_forecast_units, parse_forecast_data
from tests.test_data.sensors import ALL_INVALID_SENSORS, ALL_VALID_SENSORS


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
def test_detect_format_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test detection of valid forecast formats."""
    state = _create_sensor_state(hass, sensor_data["entity_id"], sensor_data["state"], sensor_data["attributes"])

    result = detect_format(state)

    assert result == sensor_data["expected_format"], f"Failed to detect {parser_type} format"


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_VALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_parse_forecast_data_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test parsing of valid forecast data."""
    state = _create_sensor_state(hass, sensor_data["entity_id"], sensor_data["state"], sensor_data["attributes"])

    result = parse_forecast_data(state)

    expected_count = sensor_data["expected_count"]
    if expected_count > 0:
        assert result is not None, f"Expected data for {parser_type}"
        assert len(result) == expected_count, f"Expected {expected_count} entries for {parser_type}"
        # Verify chronological order (only check if multiple entries)
        if len(result) > 1:
            assert result[0][0] < result[-1][0], f"Timestamps should be in chronological order for {parser_type}"
    else:
        assert result is None or len(result) == 0, f"Expected no data for invalid {parser_type} entry"


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_VALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_get_forecast_units_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test getting forecast units for valid sensors."""
    state = _create_sensor_state(hass, sensor_data["entity_id"], sensor_data["state"], sensor_data["attributes"])

    unit, device_class = get_forecast_units(state)

    assert unit is not None, f"Expected unit for {parser_type}"
    assert device_class is not None, f"Expected device_class for {parser_type}"


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_INVALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_invalid_sensor_handling(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test handling of invalid sensor data."""
    state = _create_sensor_state(hass, sensor_data["entity_id"], sensor_data["state"], sensor_data["attributes"])

    detected_format = detect_format(state)
    parsed_data = parse_forecast_data(state)

    expected_format = sensor_data.get("expected_format")
    expected_count = sensor_data.get("expected_count", 0)

    assert detected_format == expected_format, f"Format detection mismatch for {sensor_data['description']}"

    if expected_count > 0:
        assert parsed_data is not None
        assert len(parsed_data) == expected_count
    else:
        assert parsed_data is None or len(parsed_data) == 0


def test_detect_empty_data(hass: HomeAssistant) -> None:
    """Test detection with empty attributes."""
    state = _create_sensor_state(hass, "sensor.empty", "0", {})

    result = detect_format(state)

    assert result is None


def test_parse_unknown_format_returns_none(hass: HomeAssistant) -> None:
    """Test that parsing unknown format returns None."""
    state = _create_sensor_state(hass, "sensor.unknown", "0", {"unknown_field": "value"})

    result = parse_forecast_data(state)

    assert result is None
