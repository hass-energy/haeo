"""Helper type guards for haeo."""

from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard


def is_mapping(data: Any) -> TypeGuard[Mapping[Any, Any]]:
    """Check if data is a mapping type."""
    return isinstance(data, Mapping)


def is_sequence(data: Any) -> TypeGuard[Sequence[Any]]:
    """Check if data is a sequence type."""
    return isinstance(data, Sequence)
