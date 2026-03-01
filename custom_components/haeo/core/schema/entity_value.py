"""Schema values for entity-based inputs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict, TypeGuard

VALUE_TYPE_ENTITY = "entity"


class EntityValue(TypedDict):
    """Schema value representing entity-based inputs."""

    type: Literal["entity"]
    value: list[str]


def as_entity_value(value: list[str]) -> EntityValue:
    """Create an entity schema value from entity IDs."""
    return {"type": VALUE_TYPE_ENTITY, "value": value}


def is_entity_value(value: Any) -> TypeGuard[EntityValue]:
    """Return True if value is an entity schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_ENTITY:
        return False
    entity_list = value.get("value")
    return isinstance(entity_list, list) and all(isinstance(item, str) for item in entity_list)


__all__ = [
    "EntityValue",
    "as_entity_value",
    "is_entity_value",
]
