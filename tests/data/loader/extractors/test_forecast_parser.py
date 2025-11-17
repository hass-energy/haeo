"""Tests for data extractor functionality."""

from typing import Any

from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.haeo.data.loader import extractors
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
def test_extract_valid_sensors(hass: HomeAssistant, parser_type: str, sensor_data: dict[str, Any]) -> None:
    """Test extraction of valid forecast data."""
    state = _create_sensor_state(hass, sensor_data["entity_id"], sensor_data["state"], sensor_data["attributes"])

    result, unit = extractors.extract(state)

    expected_count = sensor_data["expected_count"]
    assert result is not None, f"Expected data for {parser_type}"
    assert isinstance(result, list), "Valid forecasts should return a list of time series entries"
    assert len(result) >= 1, f"Expected at least one entry for {parser_type}"
    if expected_count > 0:
        assert len(result) == expected_count, f"Expected {expected_count} entries for {parser_type}"
        # Verify chronological order (only check if multiple entries)
        if len(result) > 1:
            assert result[0][0] < result[-1][0], f"Timestamps should be in chronological order for {parser_type}"

    assert unit is not None, f"Expected unit for {parser_type}"


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
    result, _ = extractors.extract(state)

    # Should fall back to reading the state as a float
    assert isinstance(result, float)


def test_extract_empty_data(hass: HomeAssistant) -> None:
    """Test extraction with empty attributes falls back to simple value."""
    state = _create_sensor_state(hass, "sensor.empty", "42.0", {})

    result, _ = extractors.extract(state)

    assert isinstance(result, float)
    assert result == 42.0


# Removed test_detect_multiple_formats_warns:
# The new extract() interface doesn't expose format detection separately.
# Multiple format detection is handled internally by the extract() function.


def test_extract_unknown_format_falls_back_to_simple_value(hass: HomeAssistant) -> None:
    """Test that extracting from unknown format falls back to simple value."""
    entity_id = "sensor.unknown"
    state = _create_sensor_state(hass, entity_id, "42.5", {"unknown_field": "value"})

    result, _ = extractors.extract(state)

    assert result is not None
    # Simple value extraction returns a float directly
    assert isinstance(result, float)
    assert result == 42.5


def test_extract_unknown_format_returns_unit() -> None:
    """Extract should return sensor unit when no parser matches."""

    state = State(
        "sensor.unknown",
        "42.0",
        {
            "unit_of_measurement": "test_unit",
        },
    )

    result, unit = extractors.extract(state)
    assert isinstance(result, float)
    assert result == 42.0
    assert unit == "test_unit"


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
    extractors.amberelectric.DOMAIN: extractors.amberelectric.Parser,
    extractors.aemo_nem.DOMAIN: extractors.aemo_nem.Parser,
    extractors.solcast_solar.DOMAIN: extractors.solcast_solar.Parser,
    extractors.open_meteo_solar_forecast.DOMAIN: extractors.open_meteo_solar_forecast.Parser,
}
