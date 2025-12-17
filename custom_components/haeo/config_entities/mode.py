"""Config entity mode determination."""

from enum import StrEnum, auto


class ConfigEntityMode(StrEnum):
    """Operating mode for a config entity.

    Driven: User provided external entities in config flow. The number entity
    displays the combined output from those entities with forecast attributes.
    The entity is read-only (changes are overwritten by coordinator updates).

    Editable: User provides input via the number entity. The user's value is
    used for optimization, and forecast attributes are added while preserving
    the user's state value.

    Disabled: Optional field that isn't currently active. For required fields,
    being disabled in what would be editable mode triggers a repair issue.
    """

    DRIVEN = auto()
    EDITABLE = auto()
    DISABLED = auto()
