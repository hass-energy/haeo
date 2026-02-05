"""Schema values for connection targets."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict, TypeGuard

from .value_kinds import VALUE_TYPE_CONNECTION_TARGET


class ConnectionTargetValue(TypedDict):
    """Schema value representing a connection target."""

    type: Literal["connection_target"]
    value: str


type ConnectionTarget = ConnectionTargetValue


def as_connection_target(value: str) -> ConnectionTargetValue:
    """Create a connection target schema value."""
    return {"type": VALUE_TYPE_CONNECTION_TARGET, "value": value}


def is_connection_target(value: Any) -> TypeGuard[ConnectionTargetValue]:
    """Return True if value is a connection target schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_CONNECTION_TARGET:
        return False
    return isinstance(value.get("value"), str)


def extract_connection_target(value: ConnectionTargetValue) -> str:
    """Extract the connection target name from a schema value."""
    return value["value"]


def normalize_connection_target(value: ConnectionTargetValue | str) -> ConnectionTargetValue:
    """Normalize a connection target input into a schema value."""
    if is_connection_target(value):
        return value
    if isinstance(value, str):
        return as_connection_target(value)
    msg = f"Unsupported connection target {value!r}"
    raise TypeError(msg)


def get_connection_target_name(value: ConnectionTargetValue | str | None) -> str | None:
    """Return the connection target name for a schema value."""
    if value is None:
        return None
    if is_connection_target(value):
        return value["value"]
    if isinstance(value, str):
        return value
    msg = f"Unsupported connection target {value!r}"
    raise TypeError(msg)


__all__ = [
    "ConnectionTarget",
    "ConnectionTargetValue",
    "as_connection_target",
    "extract_connection_target",
    "get_connection_target_name",
    "is_connection_target",
    "normalize_connection_target",
]
