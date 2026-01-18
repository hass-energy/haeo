"""TrackedParam descriptor for automatic dependency tracking."""

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, overload

import numpy as np

if TYPE_CHECKING:
    from custom_components.haeo.model.element import Element

# Context for tracking parameter access during constraint computation
tracking_context: ContextVar[set[str] | None] = ContextVar("tracking", default=None)


class TrackedParam[T]:
    """Descriptor that tracks access for automatic dependency detection.

    When a constraint method accesses this parameter, the access is recorded.
    When the parameter value changes, dependent constraints are invalidated.

    Usage:
        class Battery(Element):
            capacity = TrackedParam[NDArray[np.floating[Any]]]()

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
        tracking = tracking_context.get()
        if tracking is not None:
            tracking.add(self._name)
        # Raise AttributeError if never set (standard Python behavior)
        return getattr(obj, self._private)  # type: ignore[return-value]

    def __set__(self, obj: "Element[Any]", value: T) -> None:
        """Set the parameter value and invalidate dependent decorators."""
        # Check if this is the first time setting (no invalidation needed)
        if not hasattr(obj, self._private):
            setattr(obj, self._private, value)
            return

        # Get old value and compare
        old = getattr(obj, self._private)
        setattr(obj, self._private, value)

        # Only invalidate if value actually changed
        if not _values_equal(old, value):
            # Invalidate all reactive decorators that depend on this parameter
            _invalidate_param_dependents(obj, self._name)

    def is_set(self, obj: "Element[Any]") -> bool:
        """Check if this parameter has been set on the given object.

        Args:
            obj: The element instance to check

        Returns:
            True if the parameter has been set, False otherwise

        Example:
            class MyElement(Element):
                capacity = TrackedParam[float]()

                @constraint
                def my_constraint(self) -> highs_linear_expression | None:
                    if not self.capacity.is_set(self):
                        return None  # Skip constraint until capacity is set
                    return self.energy <= self.capacity

        """
        return hasattr(obj, self._private)


def _values_equal(a: object, b: object) -> bool:
    """Compare two values for equality, handling numpy arrays.

    Args:
        a: First value
        b: Second value

    Returns:
        True if values are equal, False otherwise

    """
    # Handle numpy array comparisons
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        try:
            return bool(np.array_equal(a, b))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
    # Standard equality for other types
    try:
        return bool(a == b)
    except (TypeError, ValueError):
        return False


def _invalidate_param_dependents(element: "Element[Any]", param_name: str) -> None:
    """Invalidate all reactive decorators on an element that depend on a parameter.

    Args:
        element: The element instance
        param_name: The parameter name that changed

    """
    # Import here to avoid circular dependency at module load
    from .decorators import ReactiveMethod  # noqa: PLC0415

    # Track which methods were invalidated
    invalidated_methods: set[str] = set()

    # Iterate through all attributes on the element's class
    for attr_name in dir(type(element)):
        # Get the descriptor from the class
        descriptor = getattr(type(element), attr_name, None)
        if isinstance(descriptor, ReactiveMethod):
            # Get the state for this decorator on this element instance
            state = get_decorator_state(element, attr_name)
            if state is not None and param_name in state.get("deps", set()):
                state["invalidated"] = True
                invalidated_methods.add(attr_name)

    # Propagate invalidation to methods that depend on invalidated methods
    if invalidated_methods:
        _propagate_method_invalidation(element, invalidated_methods)


def _propagate_method_invalidation(element: "Element[Any]", invalidated_methods: set[str]) -> None:
    """Propagate invalidation to methods that depend on invalidated methods.

    Args:
        element: The element instance
        invalidated_methods: Set of method names that were invalidated

    """
    # Import here to avoid circular dependency at module load
    from .decorators import ReactiveMethod  # noqa: PLC0415

    # Keep propagating until no new invalidations occur
    newly_invalidated = invalidated_methods.copy()
    while newly_invalidated:
        next_round: set[str] = set()

        for attr_name in dir(type(element)):
            descriptor = getattr(type(element), attr_name, None)
            if isinstance(descriptor, ReactiveMethod):
                state = get_decorator_state(element, attr_name)
                # Skip if already invalidated
                if state is None or state.get("invalidated", True):
                    continue

                # Check if this method depends on any newly invalidated methods
                deps = state.get("deps", set())
                for dep in deps:
                    if dep.startswith("method:"):
                        method_name = dep[7:]  # Remove "method:" prefix
                        if method_name in newly_invalidated:
                            state["invalidated"] = True
                            next_round.add(attr_name)
                            break

        newly_invalidated = next_round


def get_decorator_state(element: "Element[Any]", method_name: str) -> dict[str, Any] | None:
    """Get the state dictionary for a decorator method on an element.

    Args:
        element: The element instance
        method_name: The method name

    Returns:
        State dictionary or None if not yet initialized

    """
    state_attr = f"_reactive_state_{method_name}"
    return getattr(element, state_attr, None)


def ensure_decorator_state(element: "Element[Any]", method_name: str) -> dict[str, Any]:
    """Ensure a state dictionary exists for a decorator method on an element.

    Args:
        element: The element instance
        method_name: The method name

    Returns:
        State dictionary (created if needed)

    """
    state_attr = f"_reactive_state_{method_name}"
    if not hasattr(element, state_attr):
        setattr(element, state_attr, {"invalidated": True, "deps": set(), "result": None})
    return getattr(element, state_attr)


# Re-export tracking context for use by decorators
__all__ = [
    "TrackedParam",
    "ensure_decorator_state",
    "get_decorator_state",
    "tracking_context",
]
