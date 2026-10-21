"""Tests for parse_datetime module."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.haeo.core.data.loader.extractors.utils.parse_datetime import (
    is_parsable_to_datetime,
    parse_datetime_to_timestamp,
)

ADELAIDE = ZoneInfo("Australia/Adelaide")
BRISBANE = ZoneInfo("Australia/Brisbane")


@pytest.mark.parametrize(
    ("value", "time_zone", "expected"),
    [
        pytest.param(
            "2025-10-06T00:00:00+11:00",
            ADELAIDE,
            datetime(2025, 10, 5, 13, 0, tzinfo=UTC),
            id="aware_string_keeps_its_offset",
        ),
        pytest.param(
            datetime(2025, 10, 6, 0, 0, tzinfo=UTC),
            ADELAIDE,
            datetime(2025, 10, 6, 0, 0, tzinfo=UTC),
            id="aware_datetime_keeps_its_zone",
        ),
        pytest.param(
            "2025-07-01T12:00:00",
            BRISBANE,
            datetime(2025, 7, 1, 2, 0, tzinfo=UTC),
            id="naive_string_in_brisbane",
        ),
        pytest.param(
            "2025-07-01T12:00:00",
            ADELAIDE,
            datetime(2025, 7, 1, 2, 30, tzinfo=UTC),
            id="naive_string_in_adelaide_standard_time",
        ),
        pytest.param(
            "2025-01-01T12:00:00",
            ADELAIDE,
            datetime(2025, 1, 1, 1, 30, tzinfo=UTC),
            id="naive_string_in_adelaide_daylight_time",
        ),
        pytest.param(
            datetime(2025, 7, 1, 12, 0),  # noqa: DTZ001  # naive on purpose
            ADELAIDE,
            datetime(2025, 7, 1, 2, 30, tzinfo=UTC),
            id="naive_datetime_in_adelaide",
        ),
        pytest.param(
            "2025-07-01T12:00:00",
            UTC,
            datetime(2025, 7, 1, 12, 0, tzinfo=UTC),
            id="naive_string_in_utc",
        ),
    ],
)
def test_parse_datetime_to_timestamp(value: str | datetime, time_zone: ZoneInfo, expected: datetime) -> None:
    """Values carrying a time zone keep it, and naive values are read in the given local time zone."""
    result = parse_datetime_to_timestamp(value, time_zone)
    assert isinstance(result, int)
    assert result == int(expected.timestamp())


def test_parse_invalid_string_raises_error() -> None:
    """Test that invalid datetime strings raise ValueError."""
    with pytest.raises(ValueError, match="Invalid isoformat string"):
        parse_datetime_to_timestamp("not a timestamp", UTC)


@pytest.mark.parametrize(
    ("value", "type_name"),
    [
        pytest.param(None, "NoneType", id="none"),
        pytest.param(12345, "int", id="int"),
        pytest.param([], "list", id="list"),
        pytest.param({}, "dict", id="dict"),
    ],
)
def test_parse_non_datetime_type_raises_error(value: object, type_name: str) -> None:
    """Test that non-datetime, non-string types raise ValueError."""
    with pytest.raises(ValueError, match=f"Expected datetime or string, got {type_name}"):
        parse_datetime_to_timestamp(value, UTC)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("2025-07-01T12:00:00", True, id="naive_string"),
        pytest.param("2025-07-01T12:00:00+09:30", True, id="aware_string"),
        pytest.param(datetime(2025, 7, 1, tzinfo=UTC), True, id="datetime"),
        pytest.param("not a timestamp", False, id="invalid_string"),
        pytest.param(12345, False, id="int"),
    ],
)
def test_is_parsable_to_datetime(value: object, *, expected: bool) -> None:
    """Strings in ISO format and datetimes are parsable whether or not they carry a time zone."""
    assert is_parsable_to_datetime(value) is expected
