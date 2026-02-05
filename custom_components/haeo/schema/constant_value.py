"""Schema values for constant inputs."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any, Literal, TypedDict, TypeGuard

VALUE_TYPE_CONSTANT = "constant"


class ConstantValue(TypedDict):
    """Schema value representing constant inputs."""

    type: Literal["constant"]
    value: float | bool


def as_constant_value(value: float | bool) -> ConstantValue:  # noqa: FBT001
    """Create a constant schema value from a scalar."""
    return {"type": VALUE_TYPE_CONSTANT, "value": value}


def is_constant_value(value: Any) -> TypeGuard[ConstantValue]:
    """Return True if value is a constant schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_CONSTANT:
        return False
    constant = value.get("value")
    if isinstance(constant, bool):
        return True
    return isinstance(constant, Real)


__all__ = [
    "ConstantValue",
    "as_constant_value",
    "is_constant_value",
]
