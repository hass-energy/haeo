"""Storage binding for input stores.

An :class:`InputStore` reads its persisted value from a ``Storage`` at
construction time and writes user edits back through it. The protocol is
intentionally tiny and Home Assistant free so the store stays a pure data
container; the integration layer supplies a concrete implementation backed by
config subentries.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Storage(Protocol):
    """Persistence binding behind an input store.

    Implementations back a single input field. ``read`` returns the stored
    schema value (entity/constant/none) or ``None`` when nothing is stored;
    ``write`` persists a new schema value.
    """

    def read(self) -> object:
        """Return the currently persisted schema value, or None."""
        ...

    async def write(self, value: object) -> None:
        """Persist a new schema value."""
        ...


__all__ = ["Storage"]
