"""Schema values for connection targets."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal, TypedDict, TypeGuard

VALUE_TYPE_CONNECTION_TARGET = "connection_target"


class ConnectionTargetValue(TypedDict):
    """Schema value representing a connection target."""

    type: Literal["connection_target"]
    value: str


type ConnectionTarget = ConnectionTargetValue


def as_connection_target(value: str) -> ConnectionTargetValue:
    """Create a connection target schema value."""
    return {"type": VALUE_TYPE_CONNECTION_TARGET, "value": value}


def is_connection_target(value: object) -> TypeGuard[ConnectionTargetValue]:
    """Return True if value is a connection target schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_CONNECTION_TARGET:
        return False
    return isinstance(value.get("value"), str)


def extract_connection_target(value: ConnectionTargetValue) -> str:
    """Extract the connection target name from a schema value."""
    return value["value"]


def normalize_connection_target(value: object) -> ConnectionTargetValue:
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


def map_connection_targets(config: Mapping[str, object], resolve: Callable[[str], str]) -> dict[str, object]:
    """Return config with every connection target in it renamed to what resolve returns for its name."""
    return {key: _map_connection_targets_in(value, resolve) for key, value in config.items()}


def _map_connection_targets_in(value: object, resolve: Callable[[str], str]) -> object:
    """Return a config value with the connection targets in it renamed."""
    if is_connection_target(value):
        return as_connection_target(resolve(value["value"]))
    if isinstance(value, Mapping):
        return {key: _map_connection_targets_in(item, resolve) for key, item in value.items()}
    if isinstance(value, list):
        return [_map_connection_targets_in(item, resolve) for item in value]
    return value


__all__ = [
    "ConnectionTarget",
    "ConnectionTargetValue",
    "as_connection_target",
    "extract_connection_target",
    "get_connection_target_name",
    "is_connection_target",
    "map_connection_targets",
    "normalize_connection_target",
]
