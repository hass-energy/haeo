"""Tests for forecast parser functionality."""

from datetime import UTC, datetime

import pytest

from custom_components.haeo.data.loader.forecast_parsers import detect_format, parse_forecast_data


@pytest.fixture
def amber_sensor(hass):
    """Create a sensor with Amber forecast data."""
    hass.states.async_set(
        "sensor.amber_forecast",
        "0.13",
        attributes={
            "forecasts": [
                {
                    "duration": 5,
                    "date": "2025-10-05",
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ]
        },
    )
    return hass.states.get("sensor.amber_forecast")


@pytest.fixture
def aemo_sensor(hass):
    """Create a sensor with AEMO forecast data."""
    hass.states.async_set(
        "sensor.aemo_forecast",
        "0.0748",
        attributes={
            "forecast": [
                {
                    "start_time": "2025-10-05T21:00:00+10:00",
                    "end_time": "2025-10-05T21:30:00+10:00",
                    "price": 0.0748,
                }
            ]
        },
    )
    return hass.states.get("sensor.aemo_forecast")


@pytest.fixture
def solcast_sensor(hass):
    """Create a sensor with Solcast forecast data."""
    hass.states.async_set(
        "sensor.solcast_forecast",
        "0",
        attributes={
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:00:00+11:00",
                    "pv_estimate": 0,
                }
            ]
        },
    )
    return hass.states.get("sensor.solcast_forecast")


@pytest.fixture
def open_meteo_sensor(hass):
    """Create a sensor with Open-Meteo forecast data."""
    hass.states.async_set(
        "sensor.open_meteo_forecast",
        "175",
        attributes={
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                "2025-10-06T07:00:00+11:00": 200,
            }
        },
    )
    return hass.states.get("sensor.open_meteo_forecast")


@pytest.fixture
def unknown_format_sensor(hass):
    """Create a sensor with unknown forecast format."""
    hass.states.async_set(
        "sensor.unknown_forecast",
        "0",
        attributes={"unknown_field": "value"},
    )
    return hass.states.get("sensor.unknown_forecast")


@pytest.fixture
def empty_sensor(hass):
    """Create a sensor with empty attributes."""
    hass.states.async_set("sensor.empty_forecast", "0", attributes={})
    return hass.states.get("sensor.empty_forecast")


@pytest.fixture
def amber_multi_forecast_sensor(hass):
    """Create a sensor with multiple Amber forecast entries."""
    hass.states.async_set(
        "sensor.amber_multi_forecast",
        "0.13",
        attributes={
            "forecasts": [
                {
                    "duration": 5,
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                },
                {
                    "duration": 5,
                    "per_kwh": 0.15,
                    "start_time": "2025-10-05T11:05:01+00:00",
                    "end_time": "2025-10-05T11:10:00+00:00",
                },
            ]
        },
    )
    return hass.states.get("sensor.amber_multi_forecast")


@pytest.fixture
def amber_timezone_sensor(hass):
    """Create a sensor with Amber forecast data with timezone."""
    hass.states.async_set(
        "sensor.amber_forecast_tz",
        "0.13",
        attributes={
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T21:00:01+10:00",  # 10:00 AM AEDT = 00:00 UTC
                }
            ]
        },
    )
    return hass.states.get("sensor.amber_forecast_tz")


@pytest.fixture
def amber_invalid_sensor(hass):
    """Create a sensor with invalid Amber forecast data."""
    hass.states.async_set(
        "sensor.amber_invalid",
        "0.13",
        attributes={
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    # Missing start_time
                },
                {
                    "start_time": "2025-10-05T11:00:01+00:00",
                    # Missing per_kwh
                },
                {
                    "per_kwh": "invalid",
                    "start_time": "2025-10-05T11:00:01+00:00",
                },
            ]
        },
    )
    return hass.states.get("sensor.amber_invalid")


@pytest.fixture
def aemo_multi_forecast_sensor(hass):
    """Create a sensor with multiple AEMO forecast entries."""
    hass.states.async_set(
        "sensor.aemo_multi_forecast",
        "0.0748",
        attributes={
            "forecast": [
                {
                    "start_time": "2025-10-05T21:00:00+10:00",
                    "end_time": "2025-10-05T21:30:00+10:00",
                    "price": 0.0748,
                },
                {
                    "start_time": "2025-10-05T21:30:00+10:00",
                    "end_time": "2025-10-05T22:00:00+10:00",
                    "price": 0.0823,
                },
            ]
        },
    )
    return hass.states.get("sensor.aemo_multi_forecast")


@pytest.fixture
def solcast_multi_forecast_sensor(hass):
    """Create a sensor with multiple Solcast forecast entries."""
    hass.states.async_set(
        "sensor.solcast_multi_forecast",
        "0",
        attributes={
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:00:00+11:00",
                    "pv_estimate": 0,
                },
                {
                    "period_start": "2025-10-06T00:15:00+11:00",
                    "pv_estimate": 10,
                },
            ]
        },
    )
    return hass.states.get("sensor.solcast_multi_forecast")


@pytest.fixture
def open_meteo_multi_forecast_sensor(hass):
    """Create a sensor with multiple Open-Meteo forecast entries."""
    hass.states.async_set(
        "sensor.open_meteo_multi_forecast",
        "175",
        attributes={
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                "2025-10-06T07:00:00+11:00": 200,
            }
        },
    )
    return hass.states.get("sensor.open_meteo_multi_forecast")


@pytest.fixture
def malformed_sensor(hass):
    """Create a sensor with malformed forecast data."""
    hass.states.async_set(
        "sensor.malformed_forecast",
        "0",
        attributes={
            "forecasts": [
                {
                    "per_kwh": "not_a_number",
                    "start_time": "2025-10-05T11:00:01+00:00",
                }
            ]
        },
    )
    return hass.states.get("sensor.malformed_forecast")


@pytest.fixture
def invalid_timestamp_sensor(hass):
    """Create a sensor with invalid timestamp data."""
    hass.states.async_set(
        "sensor.invalid_timestamp",
        "0",
        attributes={
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    "start_time": "invalid_timestamp",
                }
            ]
        },
    )
    return hass.states.get("sensor.invalid_timestamp")


def test_detect_amber_format(amber_sensor):
    """Test detection of Amber pricing format."""
    result = detect_format(amber_sensor)
    assert result == "amberelectric"


def test_detect_aemo_format(aemo_sensor):
    """Test detection of AEMO format."""
    result = detect_format(aemo_sensor)
    assert result == "aemo_nem"


def test_detect_solcast_format(solcast_sensor):
    """Test detection of Solcast format."""
    result = detect_format(solcast_sensor)
    assert result == "solcast_solar"


def test_detect_open_meteo_format(open_meteo_sensor):
    """Test detection of open-meteo format."""
    result = detect_format(open_meteo_sensor)
    assert result == "open_meteo_solar_forecast"


def test_detect_unknown_format(unknown_format_sensor):
    """Test detection of unknown format."""
    result = detect_format(unknown_format_sensor)
    assert result is None


def test_detect_empty_data(empty_sensor):
    """Test detection with empty data."""
    result = detect_format(empty_sensor)
    assert result is None


def test_parse_amber_forecast(amber_multi_forecast_sensor):
    """Test parsing of Amber forecast data."""
    result = parse_forecast_data(amber_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    # Check that timestamps are in chronological order
    assert result[0][0] < result[1][0]
    assert result[0][1] == 0.13
    assert result[1][1] == 0.15


def test_parse_amber_forecast_with_timezone(amber_timezone_sensor):
    """Test parsing Amber forecast with timezone conversion."""
    result = parse_forecast_data(amber_timezone_sensor)

    assert result is not None
    # Should convert to UTC timestamp
    expected_utc = datetime(2025, 10, 5, 11, 0, 1, tzinfo=UTC).timestamp()
    assert result[0][0] == int(expected_utc)
    assert result[0][1] == 0.13


def test_parse_amber_forecast_invalid_data(amber_invalid_sensor):
    """Test parsing Amber forecast with invalid data."""
    result = parse_forecast_data(amber_invalid_sensor)

    # Should only return valid entries
    assert result is None or len(result) == 0


def test_parse_aemo_forecast(aemo_multi_forecast_sensor):
    """Test parsing of AEMO forecast data."""
    result = parse_forecast_data(aemo_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    assert result[0][0] < result[1][0]
    assert result[0][1] == 0.0748
    assert result[1][1] == 0.0823


def test_parse_solcast_forecast(solcast_multi_forecast_sensor):
    """Test parsing of Solcast forecast data."""
    result = parse_forecast_data(solcast_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    assert result[0][0] < result[1][0]
    assert result[0][1] == 0
    assert result[1][1] == 10


def test_parse_open_meteo_forecast(open_meteo_multi_forecast_sensor):
    """Test parsing of open-meteo forecast data."""
    result = parse_forecast_data(open_meteo_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    assert result[0][0] < result[1][0]
    assert result[0][1] == 175
    assert result[1][1] == 200


def test_parse_unknown_format_returns_none(unknown_format_sensor):
    """Test that parsing unknown format returns None."""
    result = parse_forecast_data(unknown_format_sensor)
    assert result is None


def test_parse_malformed_data(malformed_sensor):
    """Test parsing malformed forecast data."""
    # Should handle gracefully and return None or empty list for invalid entries
    result = parse_forecast_data(malformed_sensor)
    assert result is None or len(result) == 0


def test_parse_invalid_timestamp(invalid_timestamp_sensor):
    """Test parsing forecast with invalid timestamp."""
    # Should handle gracefully and return None or empty list for invalid entries
    result = parse_forecast_data(invalid_timestamp_sensor)
    assert result is None or len(result) == 0
