"""Tests for datetime_utils module."""

from datetime import UTC, datetime

import pytest

from custom_components.haeo.data.loader.extractors.datetime_utils import parse_datetime_to_timestamp


def test_parse_datetime_string() -> None:
    """Test parsing ISO format datetime strings."""
    result = parse_datetime_to_timestamp("2025-10-06T00:00:00+11:00")
    assert isinstance(result, int)
    # Account for the +11:00 offset (00:00 +11:00 is 13:00 UTC previous day)
    assert result == int(datetime(2025, 10, 5, 13, 0, 0, tzinfo=UTC).timestamp())


def test_parse_datetime_object() -> None:
    """Test parsing datetime objects directly."""
    dt = datetime(2025, 10, 6, 0, 0, 0, tzinfo=UTC)
    result = parse_datetime_to_timestamp(dt)
    assert isinstance(result, int)
    assert result == int(dt.timestamp())


def test_parse_datetime_object_no_timezone() -> None:
    """Test parsing naive datetime objects (no timezone info)."""
    dt = datetime(2025, 10, 6, 12, 30, 0, tzinfo=UTC)
    result = parse_datetime_to_timestamp(dt)
    assert isinstance(result, int)


def test_parse_invalid_string_raises_error() -> None:
    """Test that invalid datetime strings raise ValueError."""
    with pytest.raises(ValueError, match="Invalid isoformat string"):
        parse_datetime_to_timestamp("not a timestamp")


def test_parse_none_raises_error() -> None:
    """Test that None input raises ValueError."""
    with pytest.raises(ValueError, match="Expected datetime or string, got NoneType"):
        parse_datetime_to_timestamp(None)


def test_parse_non_datetime_type_raises_error() -> None:
    """Test that non-datetime, non-string types raise ValueError."""
    with pytest.raises(ValueError, match="Expected datetime or string, got int"):
        parse_datetime_to_timestamp(12345)

    with pytest.raises(ValueError, match="Expected datetime or string, got list"):
        parse_datetime_to_timestamp([])

    with pytest.raises(ValueError, match="Expected datetime or string, got dict"):
        parse_datetime_to_timestamp({})
