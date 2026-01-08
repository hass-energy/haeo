"""TrackedParam descriptor for automatic dependency tracking."""

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, overload

from .types import _UNSET, UNSET, _values_equal

if TYPE_CHECKING:
    from haeo.model.element import Element

# Context for tracking parameter access during constraint computation
_tracking_context: ContextVar[set[str] | None] = ContextVar("tracking", default=None)


class TrackedParam[T]:
    """Descriptor that tracks access for automatic dependency detection.

    When a constraint method accesses this parameter, the access is recorded.
    When the parameter value changes, dependent constraints are invalidated.

    Usage:
        class Battery(Element):
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
        """Set the parameter value and invalidate dependent decorators."""
        old = getattr(obj, self._private, _UNSET)
        setattr(obj, self._private, value)
        # Only invalidate if value actually changed and is not initial set
        if old is not _UNSET and not _values_equal(old, value):
            # Invalidate all reactive decorators that depend on this parameter
            _invalidate_param_dependents(obj, self._name)


def _invalidate_param_dependents(element: "Element[Any]", param_name: str) -> None:
    """Invalidate all reactive decorators on an element that depend on a parameter.

    Args:
        element: The element instance
        param_name: The parameter name that changed

    """
    # Import here to avoid circular dependency at module load
    from .decorators import CachedMethod

    # Iterate through all attributes on the element's class
    for attr_name in dir(type(element)):
        # Get the descriptor from the class
        descriptor = getattr(type(element), attr_name, None)
        if isinstance(descriptor, CachedMethod):
            # Get the state for this decorator on this element instance
            state = _get_decorator_state(element, attr_name)
            if state is not None and param_name in state.get("deps", set()):
                state["invalidated"] = True


def _get_decorator_state(element: "Element[Any]", method_name: str) -> dict[str, Any] | None:
    """Get the state dictionary for a decorator method on an element.

    Args:
        element: The element instance
        method_name: The method name

    Returns:
        State dictionary or None if not yet initialized

    """
    state_attr = f"_reactive_state_{method_name}"
    return getattr(element, state_attr, None)


def _ensure_decorator_state(element: "Element[Any]", method_name: str) -> dict[str, Any]:
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
    "UNSET",
    "TrackedParam",
    "_ensure_decorator_state",
    "_get_decorator_state",
    "_tracking_context",
]

