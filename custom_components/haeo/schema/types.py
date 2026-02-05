"""Schema type aliases for discriminated values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from .connection_target import ConnectionTarget, ConnectionTargetValue
from .constant_value import ConstantValue
from .entity_value import EntityValue
from .none_value import NoneValue

type SchemaValueKind = Literal["entity", "constant", "none"]

type SchemaValue = EntityValue | ConstantValue | NoneValue
type SchemaContainer = Mapping[str, SchemaValue]

__all__ = [
    "ConnectionTarget",
    "ConnectionTargetValue",
    "ConstantValue",
    "EntityValue",
    "NoneValue",
    "SchemaContainer",
    "SchemaValue",
    "SchemaValueKind",
]
