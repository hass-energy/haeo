"""Tests for data extractor functionality."""

import logging
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.haeo.data.loader import extractors
from tests.test_data.sensors import ALL_INVALID_SENSORS, ALL_VALID_SENSORS, INVALID_SENSORS_BY_PARSER


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

    result = extractors.detect_format(state)

    assert result == sensor_data["expected_format"], f"Failed to detect {parser_type} format"


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_VALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_extract_time_series_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test parsing of valid forecast data."""
    entity_id = sensor_data["entity_id"]
    state = _create_sensor_state(hass, entity_id, sensor_data["state"], sensor_data["attributes"])

    result = extractors.extract_time_series(state, entity_id=entity_id)

    expected_count = sensor_data["expected_count"]
    assert result is not None, f"Expected data for {parser_type}"
    assert isinstance(result, list), "Valid forecasts should return a list of time series entries"
    assert len(result) >= 1, f"Expected at least one entry for {parser_type}"
    if expected_count > 0:
        assert len(result) == expected_count, f"Expected {expected_count} entries for {parser_type}"
        # Verify chronological order (only check if multiple entries)
        if len(result) > 1:
            assert result[0][0] < result[-1][0], f"Timestamps should be in chronological order for {parser_type}"


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_VALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_get_extracted_units_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test getting forecast units for valid sensors."""
    state = _create_sensor_state(hass, sensor_data["entity_id"], sensor_data["state"], sensor_data["attributes"])

    unit, device_class = extractors.get_extracted_units(state)

    assert unit is not None, f"Expected unit for {parser_type}"
    assert device_class is not None, f"Expected device_class for {parser_type}"


@pytest.mark.parametrize(
    ("parser_type", "sensor_data"),
    ALL_INVALID_SENSORS,
    ids=lambda val: val.get("description", str(val)) if isinstance(val, dict) else str(val),
)
def test_invalid_sensor_handling(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test handling of invalid sensor data."""
    entity_id = sensor_data["entity_id"]
    state = _create_sensor_state(hass, entity_id, sensor_data["state"], sensor_data["attributes"])

    detected_format = extractors.detect_format(state)

    expected_format = sensor_data.get("expected_format")

    assert detected_format == expected_format, f"Format detection mismatch for {sensor_data['description']}"

    # For invalid sensors, extract_time_series should either raise ValueError or fall back to simple value
    try:
        parsed_data = extractors.extract_time_series(state, entity_id=entity_id)
        # If we get here, it should have fallen back to simple value extraction
        # Simple value extraction returns a float, not a list
        assert parsed_data is not None
        assert isinstance(parsed_data, (float, list))
    except ValueError:
        # This is also acceptable for invalid sensor states
        pass


def test_detect_empty_data(hass: HomeAssistant) -> None:
    """Test detection with empty attributes."""
    state = _create_sensor_state(hass, "sensor.empty", "0", {})

    result = extractors.detect_format(state)

    assert result is None


def test_detect_multiple_formats_warns(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    """If multiple parser detectors match the payload we should warn and return None."""

    attributes = {
        "forecasts": [
            {
                "per_kwh": 0.2,
                "start_time": "2025-10-05T12:00:00+00:00",
            }
        ],
        "forecast": [
            {
                "price": 0.3,
                "start_time": "2025-10-05T12:00:00+00:00",
            }
        ],
    }
    state = _create_sensor_state(hass, "sensor.ambiguous_forecast", "0", attributes)

    with patch.object(extractors._LOGGER, "warning") as warning_mock:
        result = extractors.detect_format(state)

    assert result is None
    warning_mock.assert_called_once()
    assert "Multiple forecast formats detected" in warning_mock.call_args[0][0]


def test_extract_unknown_format_falls_back_to_simple_value(hass: HomeAssistant) -> None:
    """Test that extracting from unknown format falls back to simple value."""
    entity_id = "sensor.unknown"
    state = _create_sensor_state(hass, entity_id, "42.5", {"unknown_field": "value"})

    result = extractors.extract_time_series(state, entity_id=entity_id)

    assert result is not None
    # Simple value extraction now returns a float directly
    assert isinstance(result, float)
    assert result == 42.5


def test_get_extracted_units_unknown_format() -> None:
    """get_extracted_units should return sensor attributes when no parser matches."""

    state = State(
        "sensor.unknown",
        "0",
        {
            "unit_of_measurement": "test_unit",
            "device_class": "power",
        },
    )

    unit, device_class = extractors.get_extracted_units(state)
    assert unit == "test_unit"
    assert device_class == "power"


def test_extract_time_series_raises_for_non_numeric_state(hass: HomeAssistant) -> None:
    """Simple value extraction should raise when the sensor state is not numeric."""

    entity_id = "sensor.invalid_numeric"
    state = _create_sensor_state(
        hass,
        entity_id,
        "not-a-number",
        {"unit_of_measurement": "kWh"},
    )

    with pytest.raises(ValueError, match="Cannot parse sensor value"):
        extractors.extract_time_series(state, entity_id=entity_id)


PARSER_MAP: dict[str, extractors.DataExtractor] = {
    extractors.amberelectric.DOMAIN: extractors.amberelectric.Parser,
    extractors.aemo_nem.DOMAIN: extractors.aemo_nem.Parser,
    extractors.solcast_solar.DOMAIN: extractors.solcast_solar.Parser,
    extractors.open_meteo_solar_forecast.DOMAIN: extractors.open_meteo_solar_forecast.Parser,
}


@pytest.mark.parametrize("parser_type", sorted(PARSER_MAP))
def test_parser_extract_rejects_invalid_payloads(
    hass: HomeAssistant,
    parser_type: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each parser should reject invalid payloads even when called directly."""

    parser_cls = PARSER_MAP[parser_type]
    invalid_cases = INVALID_SENSORS_BY_PARSER[parser_type]

    for sensor in invalid_cases:
        state = _create_sensor_state(hass, sensor["entity_id"], sensor["state"], sensor["attributes"])

        with caplog.at_level(logging.WARNING, logger=parser_cls.__module__):
            result = parser_cls.extract(state)

        assert not parser_cls.detect(state)
        assert result == []
