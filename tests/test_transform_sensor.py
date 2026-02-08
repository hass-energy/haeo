"""Unit tests for transform_sensor.py script."""

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

# Import the module under test
from config import transform_sensor
from config.transform_sensor import JSONDict


@pytest.fixture
def sample_solar_data() -> JSONDict:
    """Sample solar sensor data with timestamps."""
    return {
        "entity_id": "sensor.energy_production_today_east",
        "state": "48.0245",
        "attributes": {
            "watts": {
                "2024-10-13T06:00:00Z": 0,
                "2024-10-13T12:00:00Z": 5000,
                "2024-10-13T18:00:00Z": 2000,
            },
            "wh_period": {
                "2024-10-13T06:00:00Z": 0,
                "2024-10-13T12:00:00Z": 2500,
                "2024-10-13T18:00:00Z": 1000,
            },
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "friendly_name": "Energy Production Today East",
        },
    }


@pytest.fixture
def sample_amber_forecast_data() -> JSONDict:
    """Sample Amber forecast data."""
    return {
        "entity_id": "sensor.home_general_forecast",
        "state": "10.5",
        "attributes": {
            "forecasts": [
                {
                    "start_time": "2024-10-13T00:00:00Z",
                    "end_time": "2024-10-13T00:30:00Z",
                    "per_kwh": 10.5,
                    "date": "2024-10-13",
                },
                {
                    "start_time": "2024-10-13T00:30:00Z",
                    "end_time": "2024-10-13T01:00:00Z",
                    "per_kwh": 11.2,
                    "date": "2024-10-13",
                },
                {
                    "start_time": "2024-10-13T01:00:00Z",
                    "end_time": "2024-10-13T01:30:00Z",
                    "per_kwh": 12.0,
                    "date": "2024-10-13",
                },
            ],
            "unit_of_measurement": "$/kWh",
            "friendly_name": "Home General Forecast",
        },
    }


@pytest.fixture
def sample_sigen_data() -> JSONDict:
    """Sample SiGen static sensor data."""
    return {
        "entity_id": "sensor.sigen_plant_pv_power",
        "state": "3500",
        "attributes": {
            "state_class": "measurement",
            "unit_of_measurement": "W",
            "device_class": "power",
            "icon": "mdi:solar-power",
            "friendly_name": "SiGen Plant PV Power",
        },
    }


# Tests for _transform_timestamp


def test_transform_utc_timestamp() -> None:
    """Test transforming UTC timestamp."""
    ts_str = "2024-10-13T12:30:45Z"
    target_day = datetime(2024, 10, 15, 0, 0, 0, tzinfo=UTC).timestamp()

    result = transform_sensor._transform_timestamp(ts_str, target_day)

    assert result == "2024-10-15T12:30:45Z"


def test_transform_timezone_aware_timestamp() -> None:
    """Test transforming timezone-aware timestamp."""
    ts_str = "2024-10-13T12:30:45+10:00"
    target_day = datetime(2024, 10, 15, 0, 0, 0, tzinfo=UTC).timestamp()

    result = transform_sensor._transform_timestamp(ts_str, target_day)

    # Should preserve timezone and time-of-day
    assert result == "2024-10-15T12:30:45+10:00"


def test_transform_invalid_timestamp() -> None:
    """Test transforming invalid timestamp returns original."""
    ts_str = "not-a-timestamp"
    target_day = datetime(2024, 10, 15, 0, 0, 0, tzinfo=UTC).timestamp()

    result = transform_sensor._transform_timestamp(ts_str, target_day)

    assert result == ts_str


# Tests for _transform_value_recursive


def test_transform_string_value() -> None:
    """Test transforming string value."""
    value = "test_string"

    def transform_fn(s: str) -> str:
        return s.upper()

    result = transform_sensor._transform_value_recursive(value, transform_fn)

    assert result == "TEST_STRING"


def test_transform_dict_keys_and_values() -> None:
    """Test transforming dictionary keys and values."""
    value = {"key1": "value1", "key2": "value2"}

    def transform_fn(s: str) -> str:
        return s.upper()

    result = transform_sensor._transform_value_recursive(value, transform_fn)

    assert result == {"KEY1": "VALUE1", "KEY2": "VALUE2"}


def test_transform_list_items() -> None:
    """Test transforming list items."""
    value = ["item1", "item2", "item3"]

    def transform_fn(s: str) -> str:
        return s.upper()

    result = transform_sensor._transform_value_recursive(value, transform_fn)

    assert result == ["ITEM1", "ITEM2", "ITEM3"]


def test_transform_nested_structure() -> None:
    """Test transforming nested data structure."""
    value = {
        "key1": ["item1", "item2"],
        "key2": {"nested_key": "nested_value"},
    }

    def transform_fn(s: str) -> str:
        return s.upper()

    result = transform_sensor._transform_value_recursive(value, transform_fn)

    expected = {
        "KEY1": ["ITEM1", "ITEM2"],
        "KEY2": {"NESTED_KEY": "NESTED_VALUE"},
    }
    assert result == expected


def test_transform_non_string_value() -> None:
    """Test transforming non-string value returns unchanged."""
    value = 42

    def transform_fn(s: str) -> str:
        return s.upper()

    result = transform_sensor._transform_value_recursive(value, transform_fn)

    assert result == 42


# Tests for shift_day_offset


@pytest.mark.parametrize("day_offset", [0, 1], ids=["today", "tomorrow"])
def test_shift_day_offset(sample_solar_data: JSONDict, day_offset: int) -> None:
    """Shifted timestamps match the expected day offset."""
    result = transform_sensor.shift_day_offset(sample_solar_data, day_offset)

    assert "attributes" in result
    assert "watts" in result["attributes"]

    expected_date = (datetime.now(UTC) + timedelta(days=day_offset)).date()
    for timestamp_str in result["attributes"]["watts"]:
        ts = datetime.fromisoformat(timestamp_str)
        assert ts.date() == expected_date


def test_shift_preserves_time_of_day(sample_solar_data: JSONDict) -> None:
    """Test that shifting preserves time-of-day."""
    original_times = list(sample_solar_data["attributes"]["watts"].keys())
    result = transform_sensor.shift_day_offset(sample_solar_data, 3)

    result_times = list(result["attributes"]["watts"].keys())

    # Extract times and compare
    for orig, res in zip(original_times, result_times, strict=True):
        orig_dt = datetime.fromisoformat(orig)
        res_dt = datetime.fromisoformat(res)
        assert orig_dt.time() == res_dt.time()


def test_shift_preserves_values(sample_solar_data: JSONDict) -> None:
    """Test that shifting preserves values."""
    result = transform_sensor.shift_day_offset(sample_solar_data, 2)

    # Values should be unchanged
    assert result["state"] == sample_solar_data["state"]
    original_values = list(sample_solar_data["attributes"]["watts"].values())
    result_values = list(result["attributes"]["watts"].values())
    assert original_values == result_values


# Tests for _parse_forecast_times


def test_parse_valid_forecasts(sample_amber_forecast_data: JSONDict) -> None:
    """Test parsing valid forecast data."""
    forecasts = sample_amber_forecast_data["attributes"]["forecasts"]

    result = transform_sensor._parse_forecast_times(forecasts)

    assert len(result) == 3
    assert all(isinstance(dt, datetime) for dt, _ in result)
    assert all(isinstance(fc, dict) for _, fc in result)


def test_parse_empty_forecasts() -> None:
    """Test parsing empty forecast list."""
    result = transform_sensor._parse_forecast_times([])

    assert result == []


@pytest.mark.parametrize(
    "forecasts",
    [
        pytest.param(
            [
                {"per_kwh": 10.5, "date": "2024-10-13"},
                {"start_time": "2024-10-13T00:30:00Z", "per_kwh": 11.2},
            ],
            id="missing_time_field",
        ),
        pytest.param(
            [
                {"start_time": "invalid-timestamp", "per_kwh": 10.5},
                {"start_time": "2024-10-13T00:30:00Z", "per_kwh": 11.2},
            ],
            id="invalid_timestamp",
        ),
    ],
)
def test_parse_forecasts_skips_invalid_entries(forecasts: list[JSONDict]) -> None:
    """Invalid forecast entries are skipped during parsing."""
    result = transform_sensor._parse_forecast_times(forecasts)

    assert len(result) == 1


def test_parse_forecasts_sorted_by_time() -> None:
    """Test that forecasts are sorted by time."""
    forecasts = [
        {"start_time": "2024-10-13T12:00:00Z", "per_kwh": 15.0},
        {"start_time": "2024-10-13T06:00:00Z", "per_kwh": 10.5},
        {"start_time": "2024-10-13T18:00:00Z", "per_kwh": 20.0},
    ]

    result = transform_sensor._parse_forecast_times(forecasts)

    times = [dt for dt, _ in result]
    assert times == sorted(times)


# Tests for _find_closest_time_of_day_index


def test_find_exact_match() -> None:
    """Test finding exact time-of-day match."""
    now = datetime(2024, 10, 14, 12, 0, 0, tzinfo=UTC)
    forecast_times: list[tuple[datetime, JSONDict]] = [
        (datetime(2024, 10, 13, 6, 0, 0, tzinfo=UTC), {}),
        (datetime(2024, 10, 13, 12, 0, 0, tzinfo=UTC), {}),
        (datetime(2024, 10, 13, 18, 0, 0, tzinfo=UTC), {}),
    ]

    result = transform_sensor._find_closest_time_of_day_index(forecast_times, now)

    assert result == 1


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        pytest.param(datetime(2024, 10, 14, 13, 30, 0, tzinfo=UTC), 1, id="closest_before"),
        pytest.param(datetime(2024, 10, 14, 16, 0, 0, tzinfo=UTC), 2, id="closest_after"),
    ],
)
def test_find_closest_before_or_after(now: datetime, expected: int) -> None:
    """Closest time-of-day selection handles before/after cases."""
    forecast_times: list[tuple[datetime, JSONDict]] = [
        (datetime(2024, 10, 13, 6, 0, 0, tzinfo=UTC), {}),
        (datetime(2024, 10, 13, 12, 0, 0, tzinfo=UTC), {}),
        (datetime(2024, 10, 13, 18, 0, 0, tzinfo=UTC), {}),
    ]

    result = transform_sensor._find_closest_time_of_day_index(forecast_times, now)

    assert result == expected


# Tests for _transform_forecast_timestamps


def test_transform_all_timestamp_fields() -> None:
    """Test transforming all timestamp fields in forecast."""
    forecast = {
        "start_time": "2024-10-13T12:00:00Z",
        "end_time": "2024-10-13T12:30:00Z",
        "nem_date": "2024-10-13T12:00:00Z",
        "date": "2024-10-13",
        "per_kwh": 15.5,
    }
    time_delta = timedelta(days=2, hours=3)

    result = transform_sensor._transform_forecast_timestamps(forecast, time_delta)

    assert result["start_time"] == "2024-10-15T15:00:00Z"
    assert result["end_time"] == "2024-10-15T15:30:00Z"
    assert result["nem_date"] == "2024-10-15T15:00:00Z"
    assert result["date"] == "2024-10-15"


def test_transform_preserves_z_suffix() -> None:
    """Test that Z suffix is preserved."""
    forecast = {"start_time": "2024-10-13T12:00:00Z"}
    time_delta = timedelta(days=1)

    result = transform_sensor._transform_forecast_timestamps(forecast, time_delta)

    assert result["start_time"].endswith("Z")


def test_transform_creates_copy() -> None:
    """Test that transform creates a copy."""
    forecast = {"start_time": "2024-10-13T12:00:00Z", "per_kwh": 15.5}
    time_delta = timedelta(days=1)

    result = transform_sensor._transform_forecast_timestamps(forecast, time_delta)

    assert result is not forecast
    assert forecast["start_time"] == "2024-10-13T12:00:00Z"


# Tests for wrap_forecasts


def test_wrap_forecasts_basic(sample_amber_forecast_data: JSONDict) -> None:
    """Test basic forecast wrapping."""
    result = transform_sensor.wrap_forecasts(sample_amber_forecast_data)

    assert "attributes" in result
    assert "forecasts" in result["attributes"]
    assert len(result["attributes"]["forecasts"]) == 3


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({"entity_id": "sensor.test", "state": "10"}, id="missing_attributes"),
        pytest.param(
            {
                "entity_id": "sensor.test",
                "state": "10",
                "attributes": {"forecasts": []},
            },
            id="empty_forecasts",
        ),
    ],
)
def test_wrap_forecasts_missing_or_empty(data: JSONDict) -> None:
    """wrap_forecasts returns input when no forecast data is present."""
    result = transform_sensor.wrap_forecasts(data)

    assert result == data


# Tests for passthrough


def test_passthrough_returns_unchanged(sample_sigen_data: JSONDict) -> None:
    """Test that passthrough returns data unchanged."""
    result = transform_sensor.passthrough(sample_sigen_data)

    assert result == sample_sigen_data
    assert result is sample_sigen_data


# Tests for _read_json_file


def test_read_valid_json(tmp_path: Path, sample_solar_data: JSONDict) -> None:
    """Test reading valid JSON file."""
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(sample_solar_data))

    result = transform_sensor._read_json_file(json_file)

    assert result == sample_solar_data


def test_read_nonexistent_file(tmp_path: Path) -> None:
    """Test reading nonexistent file raises FileNotFoundError."""
    json_file = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        transform_sensor._read_json_file(json_file)


def test_read_invalid_json(tmp_path: Path) -> None:
    """Test reading invalid JSON raises JSONDecodeError."""
    json_file = tmp_path / "invalid.json"
    json_file.write_text("{ invalid json }")

    with pytest.raises(json.JSONDecodeError):
        transform_sensor._read_json_file(json_file)


# Tests for _apply_transform


def test_apply_day_offset_transform(sample_solar_data: JSONDict) -> None:
    """Test applying day_offset transform."""
    result = transform_sensor._apply_transform(sample_solar_data, "day_offset", day_offset=1)

    assert "attributes" in result
    assert "watts" in result["attributes"]


def test_apply_day_offset_without_parameter(sample_solar_data: JSONDict) -> None:
    """Test applying day_offset without parameter raises ValueError."""
    with pytest.raises(ValueError, match="day_offset transform requires"):
        transform_sensor._apply_transform(sample_solar_data, "day_offset")


def test_apply_wrap_forecasts_transform(sample_amber_forecast_data: JSONDict) -> None:
    """Test applying wrap_forecasts transform."""
    result = transform_sensor._apply_transform(sample_amber_forecast_data, "wrap_forecasts")

    assert "attributes" in result
    assert "forecasts" in result["attributes"]


def test_apply_passthrough_transform(sample_sigen_data: JSONDict) -> None:
    """Test applying passthrough transform."""
    result = transform_sensor._apply_transform(sample_sigen_data, "passthrough")

    assert result == sample_sigen_data


def test_apply_unknown_transform(sample_solar_data: JSONDict) -> None:
    """Test applying unknown transform raises ValueError."""
    with pytest.raises(ValueError, match="Unknown transform type"):
        transform_sensor._apply_transform(sample_solar_data, "unknown_transform")


# Tests for _create_argument_parser


def test_parser_accepts_valid_args() -> None:
    """Test parser accepts valid arguments."""
    parser = transform_sensor._create_argument_parser()

    args = parser.parse_args(["test.json", "day_offset", "--day-offset", "1"])

    assert args.json_file == Path("test.json")
    assert args.transform_type == "day_offset"
    assert args.day_offset == 1


@pytest.mark.parametrize("transform_type", ["wrap_forecasts", "passthrough"], ids=["wrap", "passthrough"])
def test_parser_accepts_transform_types(transform_type: str) -> None:
    """Parser accepts supported transform types."""
    parser = transform_sensor._create_argument_parser()

    args = parser.parse_args(["test.json", transform_type])

    assert args.transform_type == transform_type


def test_parser_rejects_invalid_transform() -> None:
    """Test parser rejects invalid transform type."""
    parser = transform_sensor._create_argument_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["test.json", "invalid"])


def test_parser_verbose_flag() -> None:
    """Test parser accepts verbose flag."""
    parser = transform_sensor._create_argument_parser()

    args = parser.parse_args(["test.json", "passthrough", "-v"])

    assert args.verbose is True


# Tests for main function


@pytest.mark.parametrize(
    ("args", "expect_output"),
    [
        pytest.param(["passthrough"], True, id="passthrough"),
        pytest.param(["day_offset", "--day-offset", "1"], False, id="day_offset"),
    ],
)
def test_main_success(
    tmp_path: Path,
    sample_solar_data: JSONDict,
    args: list[str],
    expect_output: bool,
) -> None:
    """Test main function success paths."""
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(sample_solar_data))

    with (
        patch.object(sys, "argv", ["transform_sensor.py", str(json_file), *args]),
        patch("builtins.print") as mock_print,
    ):
        exit_code = transform_sensor.main()

    assert exit_code == 0
    mock_print.assert_called_once()
    if expect_output:
        output = json.loads(mock_print.call_args[0][0])
        assert output == sample_solar_data


def test_main_file_not_found(tmp_path: Path) -> None:
    """Test main function with nonexistent file."""
    json_file = tmp_path / "nonexistent.json"

    with patch.object(sys, "argv", ["transform_sensor.py", str(json_file), "passthrough"]):
        exit_code = transform_sensor.main()

    assert exit_code == 1


def test_main_invalid_json(tmp_path: Path) -> None:
    """Test main function with invalid JSON."""
    json_file = tmp_path / "invalid.json"
    json_file.write_text("{ invalid json }")

    with patch.object(sys, "argv", ["transform_sensor.py", str(json_file), "passthrough"]):
        exit_code = transform_sensor.main()

    assert exit_code == 1


def test_main_invalid_transform(tmp_path: Path, sample_solar_data: JSONDict) -> None:
    """Test main function with missing required parameter."""
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(sample_solar_data))

    with patch.object(sys, "argv", ["transform_sensor.py", str(json_file), "day_offset"]):
        exit_code = transform_sensor.main()

    assert exit_code == 1


def test_main_verbose_mode(tmp_path: Path, sample_solar_data: JSONDict, caplog: pytest.LogCaptureFixture) -> None:
    """Test main function with verbose mode."""
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(sample_solar_data))

    with (
        patch.object(sys, "argv", ["transform_sensor.py", str(json_file), "passthrough", "-v"]),
        patch("builtins.print"),
    ):
        transform_sensor.main()

    assert any("Verbose logging enabled" in record.message for record in caplog.records)


# Integration tests


def test_solar_forecast_transformation_workflow(tmp_path: Path) -> None:
    """Test complete solar forecast transformation workflow."""
    solar_data = {
        "entity_id": "sensor.energy_production_tomorrow_east",
        "state": "50.5",
        "attributes": {
            "watts": {
                "2024-10-13T09:00:00Z": 1000,
                "2024-10-13T15:00:00Z": 3000,
            },
            "unit_of_measurement": "kWh",
        },
    }

    json_file = tmp_path / "solar.json"
    json_file.write_text(json.dumps(solar_data))

    with (
        patch.object(sys, "argv", ["transform_sensor.py", str(json_file), "day_offset", "--day-offset", "1"]),
        patch("builtins.print") as mock_print,
    ):
        exit_code = transform_sensor.main()

    assert exit_code == 0

    output = json.loads(mock_print.call_args[0][0])

    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
    for timestamp_str in output["attributes"]["watts"]:
        ts = datetime.fromisoformat(timestamp_str)
        assert ts.date() == tomorrow


def test_amber_forecast_transformation_workflow(tmp_path: Path) -> None:
    """Test complete Amber forecast transformation workflow."""
    amber_data = {
        "entity_id": "sensor.home_general_forecast",
        "state": "12.5",
        "attributes": {
            "forecasts": [
                {
                    "start_time": "2024-10-13T00:00:00Z",
                    "per_kwh": 12.5,
                },
                {
                    "start_time": "2024-10-13T06:00:00Z",
                    "per_kwh": 15.0,
                },
            ],
            "unit_of_measurement": "$/kWh",
        },
    }

    json_file = tmp_path / "amber.json"
    json_file.write_text(json.dumps(amber_data))

    with (
        patch.object(sys, "argv", ["transform_sensor.py", str(json_file), "wrap_forecasts"]),
        patch("builtins.print") as mock_print,
    ):
        exit_code = transform_sensor.main()

    assert exit_code == 0

    output = json.loads(mock_print.call_args[0][0])

    assert len(output["attributes"]["forecasts"]) == 2


@pytest.mark.parametrize(
    ("forecast", "invalid_key", "invalid_value", "valid_key", "expected_valid"),
    [
        pytest.param(
            {
                "start_time": "not-a-valid-timestamp",
                "end_time": "2024-01-15T12:30:00Z",
            },
            "start_time",
            "not-a-valid-timestamp",
            "end_time",
            "2024-01-16T12:30:00Z",
            id="invalid_timestamp",
        ),
        pytest.param(
            {
                "date": "not-a-valid-date",
                "start_time": "2024-01-15T12:30:00Z",
            },
            "date",
            "not-a-valid-date",
            "start_time",
            "2024-01-16T12:30:00Z",
            id="invalid_date",
        ),
    ],
)
def test_transform_forecast_timestamps_handles_invalid_values(
    forecast: JSONDict,
    invalid_key: str,
    invalid_value: str,
    valid_key: str,
    expected_valid: str,
) -> None:
    """Invalid date/time strings are preserved while valid timestamps shift."""
    time_delta = timedelta(days=1)

    result = transform_sensor._transform_forecast_timestamps(forecast, time_delta)

    assert result[invalid_key] == invalid_value
    assert result[valid_key] == expected_valid


def test_transform_forecast_timestamps_handles_date_with_time() -> None:
    """Test that date fields with time components are handled correctly."""
    # Arrange
    forecast = {
        "date": "2024-01-15T12:30:00",
    }
    time_delta = timedelta(days=1)

    # Act
    result = transform_sensor._transform_forecast_timestamps(forecast, time_delta)

    # Assert - date extracted and shifted
    assert result["date"] == "2024-01-16"


def test_main_handles_unexpected_exception(tmp_path: Path) -> None:
    """Test that main handles unexpected exceptions gracefully."""
    # Arrange
    json_file = tmp_path / "test.json"
    json_file.write_text('{"key": "value"}')

    # Mock _apply_transform to raise an unexpected exception
    with patch.object(transform_sensor, "_apply_transform") as mock_apply:
        mock_apply.side_effect = RuntimeError("Unexpected error")
        with patch("sys.argv", ["transform_sensor.py", str(json_file), "passthrough"]):
            # Act
            exit_code = transform_sensor.main()

            # Assert
            assert exit_code == 1
