"""Core state interfaces used across the optimization pipeline."""

from collections.abc import Mapping
from typing import Any, Protocol


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
    def attributes(self) -> Mapping[str, Any]:
        """Entity attributes."""
        ...

    def as_dict(self) -> dict[str, Any]:
        """Return serialized state representation."""
        ...


class StateMachine(Protocol):
    """Minimal state lookup interface for core data-loading code."""

    def get(self, entity_id: str) -> EntityState | None:
        """Return entity state for *entity_id* when available."""
        ...


__all__ = ["EntityState", "StateMachine"]
