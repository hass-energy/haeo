"""Reactive parameter and constraint caching infrastructure for warm start optimization.

This module provides automatic dependency tracking for model elements, enabling
efficient warm start optimization where only changed constraints are updated.

The pattern is inspired by reactive frameworks like MobX:
- Parameters are declared as TrackedParam descriptors
- Constraint methods are decorated with @constraint
- Dependencies are tracked automatically during first execution
- Parameter changes invalidate only dependent constraints
"""

from collections.abc import Callable
from contextvars import ContextVar
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar, overload

import numpy as np

if TYPE_CHECKING:
    from .element import Element

T = TypeVar("T")

# Context for tracking parameter access during constraint computation
_tracking_context: ContextVar[set[str] | None] = ContextVar("tracking", default=None)


class CachedKind(Enum):
    """Kind of cached method for reflection-based discovery."""

    CONSTRAINT = auto()
    COST = auto()


class TrackedParam[T]:
    """Descriptor that tracks access for automatic dependency detection.

    When a constraint method accesses this parameter, the access is recorded.
    When the parameter value changes, dependent constraints are invalidated.

    Usage:
        class Battery(ReactiveElement):
            capacity = TrackedParam[Sequence[float]]()

            @constraint
            def soc_max_constraint(self) -> list[highs_linear_expression]:
                # Accessing self.capacity records dependency
                return [self.stored_energy[i] <= self.capacity[i] for i in range(self.n_periods)]

    """

    _name: str
    _private: str

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the attribute name for storage lookup."""
        self._name = name
        self._private = f"_param_{name}"

    @overload
    def __get__(self, obj: None, objtype: type) -> "TrackedParam[T]": ...

    @overload
    def __get__(self, obj: "Element[Any]", objtype: type) -> T: ...

    def __get__(self, obj: "Element[Any] | None", objtype: type) -> "TrackedParam[T] | T":
        """Get the parameter value and record access if tracking is active."""
        if obj is None:
            return self
        # Record access if tracking is active
        tracking = _tracking_context.get()
        if tracking is not None:
            tracking.add(self._name)
        # Return UNSET if the parameter has never been set
        return getattr(obj, self._private, _UNSET)  # type: ignore[return-value]

    def __set__(self, obj: "Element[Any]", value: T) -> None:
        """Set the parameter value and invalidate dependent constraints."""
        old = getattr(obj, self._private, _UNSET)
        setattr(obj, self._private, value)
        # Only invalidate if value actually changed and is not initial set
        if old is not _UNSET and not _values_equal(old, value):
            obj.invalidate_dependents(self._name)


def _values_equal(a: object, b: object) -> bool:
    """Compare two values for equality, handling numpy arrays."""
    # Handle numpy array comparisons
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        try:
            # Cast to ArrayLike to satisfy type checker
            return bool(np.array_equal(a, b))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
    # Standard equality for other types
    try:
        return bool(a == b)
    except (TypeError, ValueError):
        return False


# Sentinel for unset values
class _UnsetType:
    """Sentinel type for unset parameter values."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<UNSET>"


_UNSET = _UnsetType()

# Public alias for use in type hints and checks
UNSET: _UnsetType = _UNSET
"""Sentinel value indicating a TrackedParam has not been set.

Use `is_set()` to check if a parameter value has been set.
"""


def is_set(value: object) -> bool:
    """Check if a TrackedParam value has been set.

    Args:
        value: The value to check (from a TrackedParam access)

    Returns:
        True if the value is set (not UNSET), False otherwise

    Example:
        class MyElement(Element):
            capacity = TrackedParam[float]()

            @constraint
            def my_constraint(self) -> highs_linear_expression | None:
                if not is_set(self.capacity):
                    return None  # Skip constraint until capacity is set
                return self.energy <= self.capacity

    """
    return value is not _UNSET


class CachedMethod:
    """Base descriptor/decorator that caches method results with automatic dependency tracking.

    On first call, tracks which TrackedParam values are accessed and caches the result.
    Subsequent calls return cached result unless the method was invalidated.

    Subclasses set `kind` to distinguish constraints from costs for reflection-based discovery.
    """

    kind: CachedKind  # Set by subclasses

    def __init__(self, fn: Callable[..., Any]) -> None:
        """Initialize with the method."""
        self._fn = fn
        self._name: str = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the method name."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "CachedMethod": ...

    @overload
    def __get__(self, obj: "Element[Any]", objtype: type) -> Callable[[], Any]: ...

    def __get__(self, obj: "Element[Any] | None", objtype: type) -> "CachedMethod | Callable[[], Any]":
        """Return bound method that uses caching."""
        if obj is None:
            return self
        return partial(self._call, obj)

    def _call(self, obj: "Element[Any]") -> Any:
        """Execute with caching and dependency tracking."""
        # Return cached if not invalidated
        if obj.has_cached(self.kind, self._name) and not obj.is_invalidated(self.kind, self._name):
            return obj.get_cached(self.kind, self._name)

        # Track parameter access during computation
        tracking: set[str] = set()
        token = _tracking_context.set(tracking)
        try:
            result = self._fn(obj)
        finally:
            _tracking_context.reset(token)

        # Store result and dependencies
        obj.set_cached(self.kind, self._name, result, tracking)

        return result


class CachedConstraint(CachedMethod):
    """Decorator that caches constraint expressions with automatic dependency tracking.

    Usage:
        class Battery(ReactiveElement):
            capacity = TrackedParam[Sequence[float]]()

            @constraint
            def soc_max_constraint(self) -> list[highs_linear_expression]:
                return [self.stored_energy[i] <= self.capacity[i] for i in ...]

    """

    kind = CachedKind.CONSTRAINT


class CachedCost(CachedMethod):
    """Decorator that caches cost expressions with automatic dependency tracking."""

    kind = CachedKind.COST


class OutputMethod:
    """Decorator that marks a method as an output for reflection-based discovery.

    Unlike @constraint and @cost, output methods are not cached - they extract
    fresh values from the solver on each call. The decorator is used purely for
    reflection-based discovery via `outputs()`.

    Usage:
        class Battery(Element):
            @output
            def power_charge(self) -> OutputData:
                return OutputData(type=OutputType.POWER, unit="kW", ...)
    """

    def __init__(self, fn: Callable[..., Any]) -> None:
        """Initialize with the method."""
        self._fn = fn
        self._name: str = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the method name."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "OutputMethod": ...

    @overload
    def __get__(self, obj: "Element[Any]", objtype: type) -> Callable[[], Any]: ...

    def __get__(self, obj: "Element[Any] | None", objtype: type) -> "OutputMethod | Callable[[], Any]":
        """Return bound method."""
        if obj is None:
            return self
        return partial(self._fn, obj)


# Convenient decorator aliases
constraint = CachedConstraint
cost = CachedCost
output = OutputMethod

# Backward compatibility alias - ReactiveElement is now Element
# Import at runtime to avoid circular imports during module load
def __getattr__(name: str) -> Any:
    """Provide backward compatibility for ReactiveElement import."""
    if name == "ReactiveElement":
        from .element import Element  # noqa: PLC0415

        return Element
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
