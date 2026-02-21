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
