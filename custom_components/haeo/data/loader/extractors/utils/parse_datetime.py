"""Utility functions for datetime parsing in forecast extractors."""

from datetime import UTC, datetime
from typing import Any


def parse_datetime_to_timestamp(value: Any) -> int:
    """Parse a datetime string or datetime object to UTC timestamp.

    Args:
        value: Either a datetime object or an ISO format datetime string

    Returns:
        Unix timestamp in seconds as an integer

    Raises:
        ValueError: If value is not a valid datetime string or datetime object

    """
    # Handle datetime objects directly
    if isinstance(value, datetime):
        dt = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return int(dt.timestamp())

    # Handle string datetime values
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        dt = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        return int(dt.timestamp())

    msg = f"Expected datetime or string, got {type(value).__name__}"
    raise ValueError(msg)


def is_parsable_to_datetime(value: Any) -> bool:
    """Check if a value can be parsed to a UTC timestamp."""
    try:
        parse_datetime_to_timestamp(value)
        return True
    except (ValueError, TypeError):
        return False
