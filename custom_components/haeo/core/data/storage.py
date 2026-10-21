"""Storage binding for input stores.

An :class:`InputStore` writes user edits back through a ``Storage``. The protocol is
intentionally tiny and Home Assistant free so the store stays a pure data
container; the integration layer supplies a concrete implementation backed by
config subentries.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Storage(Protocol):
    """Persistence binding behind an input store.

    Implementations back a single input field. ``write`` persists a new
    schema value (entity/constant/none).
    """

    async def write(self, value: object) -> None:
        """Persist a new schema value."""
        ...


__all__ = ["Storage"]
