"""Schema values for disabled inputs."""

from collections.abc import Mapping
from typing import Any, Literal, TypedDict, TypeGuard

VALUE_TYPE_NONE = "none"


class NoneValue(TypedDict):
    """Schema value representing a disabled input."""

    type: Literal["none"]


def as_none_value() -> NoneValue:
    """Create a disabled schema value."""
    return {"type": VALUE_TYPE_NONE}


def is_none_value(value: Any) -> TypeGuard[NoneValue]:
    """Return True if value is a disabled schema value."""
    if not isinstance(value, Mapping):
        return False
    return value.get("type") == VALUE_TYPE_NONE


__all__ = [
    "NoneValue",
    "as_none_value",
    "is_none_value",
]
