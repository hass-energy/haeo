"""Shared constants for schema value kinds."""

from typing import Final, Literal

VALUE_TYPE_CONNECTION_TARGET: Final = "connection_target"
VALUE_TYPE_CONSTANT: Final = "constant"
VALUE_TYPE_ENTITY: Final = "entity"
VALUE_TYPE_NONE: Final = "none"

type SchemaValueKind = Literal["entity", "constant", "none"]

__all__ = [
    "VALUE_TYPE_CONNECTION_TARGET",
    "VALUE_TYPE_CONSTANT",
    "VALUE_TYPE_ENTITY",
    "VALUE_TYPE_NONE",
    "SchemaValueKind",
]
