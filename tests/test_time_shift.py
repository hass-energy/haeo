"""Unit tests for tools.time_shift."""

from datetime import UTC, datetime, timedelta

from tools.time_shift import parse_anchor_timestamp, shift_timestamps


def test_shift_timestamps_shifts_iso_string_values() -> None:
    """ISO 8601 strings are shifted by delta."""
    data = {"start_time": "2024-10-13T06:00:00Z"}
    shifted = shift_timestamps(data, timedelta(hours=2))
    assert shifted == {"start_time": "2024-10-13T08:00:00Z"}


def test_shift_timestamps_shifts_dict_keys() -> None:
    """Timestamp dict keys are shifted by delta."""
    data = {
        "watts": {
            "2024-10-13T06:00:00Z": 0,
            "2024-10-13T12:00:00Z": 5000,
        }
    }
    shifted = shift_timestamps(data, timedelta(days=1))
    assert shifted == {
        "watts": {
            "2024-10-14T06:00:00Z": 0,
            "2024-10-14T12:00:00Z": 5000,
        }
    }


def test_shift_timestamps_leaves_non_timestamps_unchanged() -> None:
    """Non-timestamp strings and numbers pass through unchanged."""
    data = {
        "friendly_name": "Solar forecast",
        "unit_of_measurement": "kWh",
        "count": 3,
    }
    shifted = shift_timestamps(data, timedelta(hours=5))
    assert shifted == data


def test_shift_timestamps_nested_forecast_list() -> None:
    """Nested forecast structures are shifted recursively."""
    data = {
        "forecasts": [
            {
                "start_time": "2024-10-13T00:00:00Z",
                "end_time": "2024-10-13T00:30:00Z",
                "per_kwh": 10.5,
            }
        ]
    }
    shifted = shift_timestamps(data, timedelta(minutes=30))
    assert shifted["forecasts"][0]["start_time"] == "2024-10-13T00:30:00Z"
    assert shifted["forecasts"][0]["end_time"] == "2024-10-13T01:00:00Z"
    assert shifted["forecasts"][0]["per_kwh"] == 10.5


def test_parse_anchor_timestamp() -> None:
    """Scenario anchor timestamps parse as timezone-aware datetimes."""
    anchor = parse_anchor_timestamp("2025-10-05T10:59:21.998507+00:00")
    assert anchor == datetime(2025, 10, 5, 10, 59, 21, 998507, tzinfo=UTC)
