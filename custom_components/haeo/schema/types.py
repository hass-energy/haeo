"""Schema type aliases for discriminated values."""

from __future__ import annotations

from typing import Literal

from .connection_target import ConnectionTarget, ConnectionTargetValue
from .constant_value import ConstantValue
from .entity_value import EntityValue
from .none_value import NoneValue

type SchemaValueKind = Literal["entity", "constant", "none"]

type SchemaValue = EntityValue | ConstantValue | NoneValue
type EntityOrConstantValue = EntityValue | ConstantValue
type OptionalEntityOrConstantValue = EntityValue | ConstantValue | NoneValue

__all__ = [
    "ConnectionTarget",
    "ConnectionTargetValue",
    "ConstantValue",
    "EntityOrConstantValue",
    "EntityValue",
    "NoneValue",
    "OptionalEntityOrConstantValue",
    "SchemaValue",
    "SchemaValueKind",
]
