"""Loader for constant (scalar) configuration values."""

from numbers import Real
from typing import Any, TypeGuard, TypeVar, overload  # noqa: TID251  # legacy Any usage; migrate to precise types

T = TypeVar("T")


class ConstantLoader[T]:
    """Loader for constant values.

    Type Parameters:
        T: The type of the constant value

    """

    @overload
    def __new__(cls, loader_type: type[float]) -> "FloatConstantLoader": ...

    @overload
    def __new__(cls, loader_type: type[T]) -> "ConstantLoader[T]": ...

    def __new__(cls, loader_type: type[Any]) -> "ConstantLoader[Any] | FloatConstantLoader":
        """Return a float-specialized loader when ``loader_type`` is ``float``."""
        if loader_type is float:
            return object.__new__(FloatConstantLoader)
        return super().__new__(cls)

    def __init__(self, loader_type: type[T]) -> None:
        """Initialize with the expected constant type."""
        self._type = loader_type

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
        if isinstance(value, self._type):
            return value

        return None


class FloatConstantLoader(ConstantLoader[float]):
    """Constant loader that coerces numeric values to float."""

    def __init__(self, loader_type: type[Any]) -> None:
        """Initialize as a float constant loader.

        ``loader_type`` must be ``float`` when created via ``ConstantLoader(float)``.
        """
        _ = loader_type
        super().__init__(float)

    def _convert(self, value: Any) -> float | None:
        """Accept any Real value and normalize to float."""
        if isinstance(value, Real):
            return float(value)

        return None
