"""Entity mode enum for HAEO entities."""

from enum import StrEnum, auto


class ConfigEntityMode(StrEnum):
    """Operating mode for a config entity.

    Driven: User provided external entities in config flow. The entity
    displays the combined output from those entities with forecast attributes.
    The entity is read-only (changes are overwritten by coordinator updates).

    Editable: User provides input via the entity. The user's value is
    used for optimization, and forecast attributes are added while preserving
    the user's state value.
    """

    DRIVEN = auto()
    EDITABLE = auto()


__all__ = ["ConfigEntityMode"]
