"""Utility functions for datetime parsing in forecast extractors."""

from datetime import datetime, tzinfo


def _parse_datetime(value: object) -> datetime:
    """Parse a datetime object or ISO format string, keeping it naive when it carries no time zone."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    msg = f"Expected datetime or string, got {type(value).__name__}"
    raise ValueError(msg)


def parse_datetime_to_timestamp(value: object, time_zone: tzinfo) -> int:
    """Parse a datetime string or datetime object to a Unix timestamp.

    Args:
        value: Either a datetime object or an ISO format datetime string
        time_zone: Time zone of values that carry none, which sources write
            in local time

    Returns:
        Unix timestamp in seconds as an integer

    Raises:
        ValueError: If value is not a valid datetime string or datetime object

    """
    dt = _parse_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=time_zone)
    return int(dt.timestamp())


def is_parsable_to_datetime(value: object) -> bool:
    """Check if a value can be parsed to a datetime."""
    try:
        _parse_datetime(value)
        return True
    except (ValueError, TypeError):
        return False
