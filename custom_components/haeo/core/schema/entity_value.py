"""Schema values for entity-based inputs."""

from collections.abc import Mapping, Sequence
from typing import Literal, NotRequired, TypedDict, TypeGuard

VALUE_TYPE_ENTITY = "entity"


class EntityValue(TypedDict):
    """Schema value representing entity-based inputs.

    An on/off input reading entities whose states are words, such as a
    charger reporting ``Charging`` or ``Idle``, lists which states mean on
    and which mean off.
    """

    type: Literal["entity"]
    value: Sequence[str]
    on_states: NotRequired[Sequence[str]]
    off_states: NotRequired[Sequence[str]]


def as_entity_value(value: list[str], *, on_states: Sequence[str] = (), off_states: Sequence[str] = ()) -> EntityValue:
    """Create an entity schema value from entity IDs, with the states that mean on and off when given."""
    entity_value: EntityValue = {"type": VALUE_TYPE_ENTITY, "value": value}
    if on_states:
        entity_value["on_states"] = list(on_states)
    if off_states:
        entity_value["off_states"] = list(off_states)
    return entity_value


def is_entity_value(value: object) -> TypeGuard[EntityValue]:
    """Return True if value is an entity schema value.

    Accepts any sequence for the value field because HA's
    config entry deep-freeze converts lists to tuples.
    """
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_ENTITY:
        return False
    entity_list = value.get("value")
    return (
        isinstance(entity_list, Sequence)
        and not isinstance(entity_list, str)
        and all(isinstance(item, str) for item in entity_list)
    )


__all__ = [
    "EntityValue",
    "as_entity_value",
    "is_entity_value",
]
