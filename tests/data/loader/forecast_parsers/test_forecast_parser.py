"""Tests for forecast parser functionality."""

from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.haeo.data.loader.forecast_parsers import detect_format, get_forecast_units, parse_forecast_data


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


@pytest.fixture
def amber_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with Amber forecast data."""
    return _create_sensor_state(
        hass,
        "sensor.amber_forecast",
        "0.13",
        {
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


@pytest.fixture
def aemo_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with AEMO forecast data."""
    return _create_sensor_state(
        hass,
        "sensor.aemo_forecast",
        "0.0748",
        {
            "forecast": [
                {
                    "start_time": "2025-10-05T21:00:00+10:00",
                    "end_time": "2025-10-05T21:30:00+10:00",
                    "price": 0.0748,
                }
            ]
        },
    )


@pytest.fixture
def solcast_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with Solcast forecast data."""
    return _create_sensor_state(
        hass,
        "sensor.solcast_forecast",
        "0",
        {
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:00:00+11:00",
                    "pv_estimate": 0,
                }
            ]
        },
    )


@pytest.fixture
def open_meteo_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with Open-Meteo forecast data."""
    return _create_sensor_state(
        hass,
        "sensor.open_meteo_forecast",
        "175",
        {
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                "2025-10-06T07:00:00+11:00": 200,
            }
        },
    )


@pytest.fixture
def unknown_format_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with unknown forecast format."""
    return _create_sensor_state(
        hass,
        "sensor.unknown_forecast",
        "0",
        {"unknown_field": "value"},
    )


@pytest.fixture
def empty_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with empty attributes."""
    return _create_sensor_state(
        hass,
        "sensor.empty_forecast",
        "0",
        {},
    )


@pytest.fixture
def amber_multi_forecast_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with multiple Amber forecast entries."""
    return _create_sensor_state(
        hass,
        "sensor.amber_multi_forecast",
        "0.13",
        {
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


@pytest.fixture
def amber_timezone_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with Amber forecast data with timezone."""
    return _create_sensor_state(
        hass,
        "sensor.amber_forecast_tz",
        "0.13",
        {
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T21:00:01+10:00",  # 10:00 AM AEDT = 00:00 UTC
                }
            ]
        },
    )


@pytest.fixture
def amber_invalid_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with invalid Amber forecast data."""
    return _create_sensor_state(
        hass,
        "sensor.amber_invalid",
        "0.13",
        {
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


@pytest.fixture
def aemo_multi_forecast_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with multiple AEMO forecast entries."""
    return _create_sensor_state(
        hass,
        "sensor.aemo_multi_forecast",
        "0.0748",
        {
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


@pytest.fixture
def solcast_multi_forecast_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with multiple Solcast forecast entries."""
    return _create_sensor_state(
        hass,
        "sensor.solcast_multi_forecast",
        "0",
        {
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


@pytest.fixture
def open_meteo_multi_forecast_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with multiple Open-Meteo forecast entries."""
    return _create_sensor_state(
        hass,
        "sensor.open_meteo_multi_forecast",
        "175",
        {
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                "2025-10-06T07:00:00+11:00": 200,
            }
        },
    )


@pytest.fixture
def malformed_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with malformed forecast data."""
    return _create_sensor_state(
        hass,
        "sensor.malformed_forecast",
        "0",
        {
            "forecasts": [
                {
                    "per_kwh": "not_a_number",
                    "start_time": "2025-10-05T11:00:01+00:00",
                }
            ]
        },
    )


@pytest.fixture
def invalid_timestamp_sensor(hass: HomeAssistant) -> State:
    """Create a sensor with invalid timestamp data."""
    return _create_sensor_state(
        hass,
        "sensor.invalid_timestamp",
        "0",
        {
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    "start_time": "invalid_timestamp",
                }
            ]
        },
    )


def test_detect_amber_format(amber_sensor: State) -> None:
    """Test detection of Amber pricing format."""
    result = detect_format(amber_sensor)
    assert result == "amberelectric"


def test_detect_aemo_format(aemo_sensor: State) -> None:
    """Test detection of AEMO format."""
    result = detect_format(aemo_sensor)
    assert result == "aemo_nem"


def test_detect_solcast_format(solcast_sensor: State) -> None:
    """Test detection of Solcast format."""
    result = detect_format(solcast_sensor)
    assert result == "solcast_solar"


def test_detect_open_meteo_format(open_meteo_sensor: State) -> None:
    """Test detection of open-meteo format."""
    result = detect_format(open_meteo_sensor)
    assert result == "open_meteo_solar_forecast"


def test_detect_unknown_format(unknown_format_sensor: State) -> None:
    """Test detection of unknown format."""
    result = detect_format(unknown_format_sensor)
    assert result is None


def test_detect_empty_data(empty_sensor: State) -> None:
    """Test detection with empty data."""
    result = detect_format(empty_sensor)
    assert result is None


def test_parse_amber_forecast(amber_multi_forecast_sensor: State) -> None:
    """Test parsing of Amber forecast data."""
    result = parse_forecast_data(amber_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    # Check that timestamps are in chronological order
    assert result[0][0] < result[1][0]
    assert result[0][1] == 0.13
    assert result[1][1] == 0.15


def test_parse_amber_forecast_with_timezone(amber_timezone_sensor: State) -> None:
    """Test parsing Amber forecast with timezone conversion."""
    result = parse_forecast_data(amber_timezone_sensor)

    assert result is not None
    # Should convert to UTC timestamp
    expected_utc = datetime(2025, 10, 5, 11, 0, 1, tzinfo=UTC).timestamp()
    assert result[0][0] == int(expected_utc)
    assert result[0][1] == 0.13


def test_parse_amber_forecast_invalid_data(amber_invalid_sensor: State) -> None:
    """Test parsing Amber forecast with invalid data."""
    result = parse_forecast_data(amber_invalid_sensor)

    # Should only return valid entries
    assert result is None or len(result) == 0


def test_parse_aemo_forecast(aemo_multi_forecast_sensor: State) -> None:
    """Test parsing of AEMO forecast data."""
    result = parse_forecast_data(aemo_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    assert result[0][0] < result[1][0]
    assert result[0][1] == 0.0748
    assert result[1][1] == 0.0823


def test_parse_solcast_forecast(solcast_multi_forecast_sensor: State) -> None:
    """Test parsing of Solcast forecast data."""
    result = parse_forecast_data(solcast_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    assert result[0][0] < result[1][0]
    assert result[0][1] == 0
    assert result[1][1] == 10


def test_parse_open_meteo_forecast(open_meteo_multi_forecast_sensor: State) -> None:
    """Test parsing of open-meteo forecast data."""
    result = parse_forecast_data(open_meteo_multi_forecast_sensor)

    assert result is not None
    assert len(result) == 2
    assert result[0][0] < result[1][0]
    # Values should be raw (in watts), conversion happens in ForecastLoader
    assert result[0][1] == 175
    assert result[1][1] == 200


def test_parse_unknown_format_returns_none(unknown_format_sensor: State) -> None:
    """Test that parsing unknown format returns None."""
    result = parse_forecast_data(unknown_format_sensor)
    assert result is None


def test_parse_malformed_data(malformed_sensor: State) -> None:
    """Test parsing malformed forecast data."""
    # Should handle gracefully and return None or empty list for invalid entries
    result = parse_forecast_data(malformed_sensor)
    assert result is None or len(result) == 0


def test_parse_invalid_timestamp(invalid_timestamp_sensor: State) -> None:
    """Test parsing forecast with invalid timestamp."""
    # Should handle gracefully and return None or empty list for invalid entries
    result = parse_forecast_data(invalid_timestamp_sensor)
    assert result is None or len(result) == 0


# Edge case tests for parser robustness


def test_aemo_detect_no_forecast_attribute(hass: HomeAssistant) -> None:
    """Test AEMO detect() with missing forecast attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.aemo_nem import Parser

    state = _create_sensor_state(hass, "sensor.no_forecast", "0", {})
    assert Parser.detect(state) is False


def test_aemo_detect_forecast_not_list(hass: HomeAssistant) -> None:
    """Test AEMO detect() with forecast not being a list."""
    from custom_components.haeo.data.loader.forecast_parsers.aemo_nem import Parser

    state = _create_sensor_state(hass, "sensor.bad_forecast", "0", {"forecast": "not a list"})
    assert Parser.detect(state) is False


def test_aemo_detect_empty_forecast(hass: HomeAssistant) -> None:
    """Test AEMO detect() with empty forecast list."""
    from custom_components.haeo.data.loader.forecast_parsers.aemo_nem import Parser

    state = _create_sensor_state(hass, "sensor.empty_forecast", "0", {"forecast": []})
    assert Parser.detect(state) is False


def test_aemo_extract_invalid_item_types(hass: HomeAssistant) -> None:
    """Test AEMO extract() handles non-dict items gracefully."""
    from custom_components.haeo.data.loader.forecast_parsers.aemo_nem import Parser

    state = _create_sensor_state(
        hass,
        "sensor.invalid_items",
        "0",
        {"forecast": ["string", 123, None, {"start_time": "2024-01-01T00:00:00Z", "price": 0.1}]},
    )
    result = Parser.extract(state)
    assert len(result) == 1  # Only the valid item


def test_aemo_extract_missing_fields(hass: HomeAssistant) -> None:
    """Test AEMO extract() handles items with missing required fields."""
    from custom_components.haeo.data.loader.forecast_parsers.aemo_nem import Parser

    state = _create_sensor_state(
        hass,
        "sensor.missing_fields",
        "0",
        {
            "forecast": [
                {"start_time": "2024-01-01T00:00:00Z"},  # Missing price
                {"price": 0.1},  # Missing start_time
                {"start_time": "2024-01-01T00:00:00Z", "price": 0.1},  # Valid
            ]
        },
    )
    result = Parser.extract(state)
    assert len(result) == 1  # Only the valid item


def test_aemo_extract_invalid_timestamp(hass: HomeAssistant) -> None:
    """Test AEMO extract() handles invalid timestamps gracefully."""
    from custom_components.haeo.data.loader.forecast_parsers.aemo_nem import Parser

    state = _create_sensor_state(
        hass, "sensor.bad_timestamp", "0", {"forecast": [{"start_time": "not a timestamp", "price": 0.1}]}
    )
    result = Parser.extract(state)
    assert len(result) == 0  # Invalid timestamp skipped


def test_amberelectric_detect_no_forecasts_attribute(hass: HomeAssistant) -> None:
    """Test Amber detect() with missing forecasts attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.amberelectric import Parser

    state = _create_sensor_state(hass, "sensor.no_forecasts", "0", {})
    assert Parser.detect(state) is False


def test_amberelectric_detect_forecasts_not_list(hass: HomeAssistant) -> None:
    """Test Amber detect() with forecasts not being a list."""
    from custom_components.haeo.data.loader.forecast_parsers.amberelectric import Parser

    state = _create_sensor_state(hass, "sensor.bad_forecasts", "0", {"forecasts": "not a list"})
    assert Parser.detect(state) is False


def test_amberelectric_extract_invalid_timestamp(hass: HomeAssistant) -> None:
    """Test Amber extract() handles invalid timestamps gracefully."""
    from custom_components.haeo.data.loader.forecast_parsers.amberelectric import Parser

    state = _create_sensor_state(
        hass, "sensor.bad_timestamp", "0", {"forecasts": [{"start_time": "not a timestamp", "per_kwh": 0.1}]}
    )
    result = Parser.extract(state)
    assert len(result) == 0  # Invalid timestamp skipped


def test_solcast_detect_no_detailedForecast_attribute(hass: HomeAssistant) -> None:
    """Test Solcast detect() with missing detailedForecast attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.solcast_solar import Parser

    state = _create_sensor_state(hass, "sensor.no_detailed_forecast", "0", {})
    assert Parser.detect(state) is False


def test_solcast_detect_detailedForecast_not_list(hass: HomeAssistant) -> None:
    """Test Solcast detect() with detailedForecast not being a list."""
    from custom_components.haeo.data.loader.forecast_parsers.solcast_solar import Parser

    state = _create_sensor_state(hass, "sensor.bad_detailed_forecast", "0", {"detailedForecast": "not a list"})
    assert Parser.detect(state) is False


def test_solcast_extract_invalid_timestamp(hass: HomeAssistant) -> None:
    """Test Solcast extract() handles invalid timestamps gracefully."""
    from custom_components.haeo.data.loader.forecast_parsers.solcast_solar import Parser

    state = _create_sensor_state(
        hass,
        "sensor.bad_timestamp",
        "0",
        {"detailedForecast": [{"period_start": "not a timestamp", "pv_estimate": 100}]},
    )
    result = Parser.extract(state)
    assert len(result) == 0  # Invalid timestamp skipped


def test_open_meteo_detect_no_watts_attribute(hass: HomeAssistant) -> None:
    """Test Open-Meteo detect() with missing watts attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.open_meteo_solar_forecast import Parser

    state = _create_sensor_state(hass, "sensor.no_watts", "0", {})
    assert Parser.detect(state) is False


def test_open_meteo_detect_watts_not_dict(hass: HomeAssistant) -> None:
    """Test Open-Meteo detect() with watts not being a dict."""
    from custom_components.haeo.data.loader.forecast_parsers.open_meteo_solar_forecast import Parser

    state = _create_sensor_state(hass, "sensor.bad_watts", "0", {"watts": "not a dict"})
    assert Parser.detect(state) is False


def test_open_meteo_extract_invalid_timestamp(hass: HomeAssistant) -> None:
    """Test Open-Meteo extract() handles invalid timestamps gracefully."""
    from custom_components.haeo.data.loader.forecast_parsers.open_meteo_solar_forecast import Parser

    state = _create_sensor_state(hass, "sensor.bad_timestamp", "0", {"watts": {"not a timestamp": 100}})
    result = Parser.extract(state)
    assert len(result) == 0  # Invalid timestamp skipped


def test_detect_multiple_formats_warning(hass: HomeAssistant) -> None:
    """Test that multiple matching formats returns None (with warning logged)."""
    # Create a sensor with attributes matching multiple parsers
    # This is an edge case but theoretically possible with overlapping attribute patterns
    state = _create_sensor_state(
        hass,
        "sensor.multi_format",
        "0.13",
        {
            # Amber format
            "forecasts": [
                {
                    "duration": 5,
                    "date": "2025-10-05",
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ],
            # AEMO format
            "forecast": [
                {
                    "start_time": "2025-10-05T21:00:00+10:00",
                    "end_time": "2025-10-05T21:30:00+10:00",
                    "price": 0.0748,
                }
            ],
        },
    )

    # When multiple formats match, returns None (and logs warning - see test output)
    result = detect_format(state)
    assert result is None


def test_get_forecast_units_unknown_format(unknown_format_sensor: State) -> None:
    """Test get_forecast_units raises ValueError for unknown format."""
    with pytest.raises(ValueError, match=r"Cannot get forecast units for unknown format"):
        get_forecast_units(unknown_format_sensor)


def test_get_forecast_units_valid_format(amber_sensor: State) -> None:
    """Test get_forecast_units returns unit and device class for valid format."""
    unit, device_class = get_forecast_units(amber_sensor)
    assert unit is not None
    assert device_class is not None


def test_amberelectric_parser_with_non_list_forecasts(hass: HomeAssistant) -> None:
    """Test Amber parser handles non-list forecasts attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.amberelectric import Parser

    state = _create_sensor_state(hass, "sensor.amber_bad", "0.13", {"forecasts": "not a list"})

    result = Parser.extract(state)

    assert result == []


def test_amberelectric_parser_with_non_dict_items(hass: HomeAssistant) -> None:
    """Test Amber parser handles non-dict items in forecasts."""
    from custom_components.haeo.data.loader.forecast_parsers.amberelectric import Parser

    state = _create_sensor_state(
        hass,
        "sensor.amber_bad",
        "0.13",
        {
            "forecasts": [
                "not a dict",
                123,
                None,
                {"start_time": "2024-01-01T00:00:00+00:00", "per_kwh": 0.25},
            ]
        },
    )

    result = Parser.extract(state)

    # Should skip non-dict items and only process the valid one
    assert len(result) == 1


def test_aemo_parser_with_non_list_forecast(hass: HomeAssistant) -> None:
    """Test AEMO parser handles non-list forecast attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.aemo_nem import Parser

    state = _create_sensor_state(hass, "sensor.aemo_bad", "0.0748", {"forecast": "not a list"})

    result = Parser.extract(state)

    assert result == []


def test_solcast_parser_with_non_list_forecast(hass: HomeAssistant) -> None:
    """Test Solcast parser handles non-list detailedForecast attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.solcast_solar import Parser

    state = _create_sensor_state(hass, "sensor.solcast_bad", "0", {"detailedForecast": "not a list"})

    result = Parser.extract(state)

    assert result == []


def test_solcast_parser_with_non_dict_items(hass: HomeAssistant) -> None:
    """Test Solcast parser handles non-dict items in detailedForecast."""
    from custom_components.haeo.data.loader.forecast_parsers.solcast_solar import Parser

    state = _create_sensor_state(
        hass,
        "sensor.solcast_bad",
        "0",
        {
            "detailedForecast": [
                "not a dict",
                123,
                {"period_start": "2024-01-01T00:00:00.0000000Z", "pv_estimate": 0.5},
            ]
        },
    )

    result = Parser.extract(state)

    # Should skip non-dict items and only process the valid one
    assert len(result) == 1


def test_solcast_parser_with_missing_fields(hass: HomeAssistant) -> None:
    """Test Solcast parser handles items with missing required fields."""
    from custom_components.haeo.data.loader.forecast_parsers.solcast_solar import Parser

    state = _create_sensor_state(
        hass,
        "sensor.solcast_bad",
        "0",
        {
            "detailedForecast": [
                {"period_start": "2024-01-01T00:00:00.0000000Z"},  # Missing pv_estimate
                {"pv_estimate": 0.5},  # Missing period_start
                {"period_start": None, "pv_estimate": 0.5},  # period_start is None
                {"period_start": "2024-01-01T01:00:00.0000000Z", "pv_estimate": None},  # pv_estimate is None
                {"period_start": "2024-01-01T02:00:00.0000000Z", "pv_estimate": 1.0},  # Valid
            ]
        },
    )

    result = Parser.extract(state)

    # Should only process the valid item
    assert len(result) == 1
    assert result[0][1] == 1.0


def test_open_meteo_parser_with_non_dict_watts(hass: HomeAssistant) -> None:
    """Test Open-Meteo parser handles non-dict watts attribute."""
    from custom_components.haeo.data.loader.forecast_parsers.open_meteo_solar_forecast import Parser

    state = _create_sensor_state(hass, "sensor.open_meteo_bad", "175", {"watts": "not a dict"})

    result = Parser.extract(state)

    assert result == []


def test_open_meteo_parser_with_invalid_datetime_keys(hass: HomeAssistant) -> None:
    """Test Open-Meteo parser handles invalid datetime keys in watts."""
    from custom_components.haeo.data.loader.forecast_parsers.open_meteo_solar_forecast import Parser

    # watts dict with invalid datetime key should return False from detect()
    state = _create_sensor_state(hass, "sensor.open_meteo_bad", "175", {"watts": {"not_a_datetime": 100}})

    # detect() will return False, so we're testing that the parser gracefully rejects this
    result = Parser.detect(state)

    assert result is False
