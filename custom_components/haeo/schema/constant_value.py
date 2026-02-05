"""Schema values for constant inputs."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import TYPE_CHECKING, Any, Literal, TypedDict, TypeGuard

from .value_kinds import VALUE_TYPE_CONSTANT

if TYPE_CHECKING:
    from .types import SchemaValue


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


def extract_constant(value: SchemaValue) -> float | bool | None:
    """Extract constant scalar from a schema value."""
    if value["type"] == VALUE_TYPE_CONSTANT:
        return value["value"]
    return None


__all__ = [
    "ConstantValue",
    "as_constant_value",
    "extract_constant",
    "is_constant_value",
]
