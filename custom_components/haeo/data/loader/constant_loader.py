"""Loader for constant (scalar) configuration values."""

from typing import Any


class ConstantLoader[T]:
    """Loader for constant values.

    Type Parameters:
        T: The type of the constant value

    """

    def available(self, **_kwargs: Any) -> bool:
        """Return True if the constant field is available."""
        return True  # Constants are always available

    async def load(self, *, value: T, **_kwargs: Any) -> T:
        """Load the constant field value."""
        return value
