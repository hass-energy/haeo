"""Core state interfaces used across the optimization pipeline."""

from collections.abc import Mapping
from datetime import tzinfo
from typing import Final, Protocol

# States Home Assistant uses for an entity without a reading
NO_READING_STATES: Final = frozenset({"unavailable", "unknown"})

# States that read as on or off, as binary sensors and booleans report them, with the number each reads as
ON_OFF_STATE_VALUES: Final[Mapping[str, float]] = {"on": 1.0, "true": 1.0, "off": 0.0, "false": 0.0}


class EntityState(Protocol):
    """Entity state shape required by the core pipeline."""

    @property
    def entity_id(self) -> str:
        """Entity identifier."""
        ...

    @property
    def state(self) -> str:
        """Raw state string."""
        ...

    @property
    def attributes(self) -> Mapping[str, object]:
        """Entity attributes."""
        ...

    def as_dict(self) -> Mapping[str, object]:
        """Return serialized state representation."""
        ...


class StateMachine(Protocol):
    """Minimal state lookup interface for core data-loading code."""

    @property
    def time_zone(self) -> tzinfo:
        """Local time zone, in which timestamps without a time zone are read."""
        ...

    def get(self, entity_id: str) -> EntityState | None:
        """Return entity state for *entity_id* when available."""
        ...


__all__ = ["NO_READING_STATES", "ON_OFF_STATE_VALUES", "EntityState", "StateMachine"]
