"""Uniform timestamp shifting for scenario input replay."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

# JSON value shape handled by shift_timestamps (Mapping/Sequence so concrete
# dict/list types are accepted covariantly). Local alias so this tool stays
# importable without Home Assistant installed.
type JsonValue = str | int | float | bool | None | Mapping[str, "JsonValue"] | Sequence["JsonValue"]


def _shift_timestamp(value: str, delta: timedelta) -> str:
    """Shift an ISO 8601 timestamp string by delta, preserving format where possible."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value

    shifted = parsed + delta

    if value.endswith("Z"):
        return shifted.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    if parsed.tzinfo is None and shifted.tzinfo is not None:
        shifted = shifted.replace(tzinfo=None)

    return shifted.isoformat()


def shift_timestamps(data: JsonValue, delta: timedelta) -> JsonValue:
    """Recursively shift ISO 8601 timestamps in nested data by delta.

    Dict keys that parse as timestamps are shifted as well as string values.
    Non-timestamp strings and other scalar types pass through unchanged.
    """
    if isinstance(data, str):
        return _shift_timestamp(data, delta)

    if isinstance(data, dict):
        return {_shift_timestamp(key, delta): shift_timestamps(value, delta) for key, value in data.items()}

    if isinstance(data, list):
        return [shift_timestamps(item, delta) for item in data]

    return data


def parse_anchor_timestamp(value: str) -> datetime:
    """Parse a scenario environment optimization_start_time value."""
    return datetime.fromisoformat(value)
