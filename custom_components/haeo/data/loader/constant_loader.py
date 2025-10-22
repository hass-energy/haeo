"""Loader for constant (scalar) configuration values."""

from typing import Any, TypeGuard


class ConstantLoader[T]:
    """Loader for constant values.

    Type Parameters:
        T: The type of the constant value

    """

    def __init__(self, cls: type[T]) -> None:
        """Initialize with the expected constant type."""
        self._type = cls

    def available(self, value: Any, **_kwargs: Any) -> bool:
        """Return True if the constant field is available."""
        if not self.is_valid_value(value):
            msg = f"Value must be of type {self._type}"
            raise TypeError(msg)

        return True  # Constants are always available

    async def load(self, *, value: Any, **_kwargs: Any) -> T:
        """Load the constant field value."""
        if not self.is_valid_value(value):
            msg = f"Value must be of type {self._type}"
            raise TypeError(msg)

        return value

    def is_valid_value(self, value: Any) -> TypeGuard[T]:
        """Check if the value is of the expected constant type."""
        return isinstance(value, self._type)
