"""Loader for constant (scalar) configuration values."""

from numbers import Real
from typing import Any, TypeGuard, cast


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
        if self._convert(value) is None:
            msg = f"Value must be of type {self._type}"
            raise TypeError(msg)

        return True  # Constants are always available

    async def load(self, *, value: Any, **_kwargs: Any) -> T:
        """Load the constant field value."""
        converted = self._convert(value)
        if converted is None:
            msg = f"Value must be of type {self._type}"
            raise TypeError(msg)

        return converted

    def is_valid_value(self, value: Any) -> TypeGuard[T]:
        """Check if the value is of the expected constant type."""
        return self._convert(value) is not None

    def _convert(self, value: Any) -> T | None:
        """Return the converted value when it matches the expected type."""

        if self._type is float:
            if isinstance(value, Real):
                return cast("T", float(value))
            return None

        if isinstance(value, self._type):
            return value

        return None
