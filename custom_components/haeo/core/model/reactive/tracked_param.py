"""TrackedParam descriptor for automatic dependency tracking."""

from contextvars import ContextVar
from typing import NotRequired, TypedDict, overload

from highspy.highs import highs_cons, highs_linear_expression
import numpy as np

from .protocols import ReactiveHost

type Dependency = tuple[ReactiveHost, str]
"""A value a reactive method read: its host and the parameter name or ``method:<name>`` key."""


class DecoratorState(TypedDict):
    """Reactive cache state stored per decorated method on a ReactiveHost instance.

    ``result`` is typed ``object`` because it holds whatever the decorated method
    returns (constraint expressions, cost expressions, ...); callers already narrow
    or ``# type: ignore`` at the point they read it back out through the generic
    ``ReactiveMethod[R]``/``ReactiveConstraint[R]`` machinery.
    """

    invalidated: bool
    deps: set[Dependency]
    result: object
    constraint: NotRequired[highs_cons | list[highs_cons]]
    applied: NotRequired[highs_linear_expression | list[highs_linear_expression]]


# Context for tracking parameter access during constraint computation
tracking_context: ContextVar[set[Dependency] | None] = ContextVar("tracking", default=None)

# Attribute on each host holding the reverse index from its keys to dependent methods
_DEPENDENTS_ATTR = "_reactive_dependents"


class TrackedParam[T]:
    """Descriptor that tracks access for automatic dependency detection.

    When a constraint method accesses this parameter, the access is recorded.
    When the parameter value changes, dependent constraints are invalidated.

    Can be used on any class satisfying the ReactiveHost protocol (Element, Segment, etc).

    Usage:
        class Battery(Element):
            capacity = TrackedParam[NDArray[np.float64]]()

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
    def __get__(self, obj: ReactiveHost, objtype: type) -> T: ...

    def __get__(self, obj: "ReactiveHost | None", objtype: type) -> "TrackedParam[T] | T":
        """Get the parameter value and record access if tracking is active."""
        if obj is None:
            return self
        record_access(obj, self._name)
        # Raise AttributeError if never set (standard Python behavior)
        return getattr(obj, self._private)  # type: ignore[return-value]

    def __set__(self, obj: ReactiveHost, value: T) -> None:
        """Set the parameter value and invalidate everything that read it, if it changed.

        A first assignment always counts as a change, so a method that checked
        ``is_set`` before the parameter existed is rebuilt.
        """
        changed = not hasattr(obj, self._private) or not _values_equal(getattr(obj, self._private), value)
        setattr(obj, self._private, value)
        if changed:
            _invalidate_param_dependents(obj, self._name)

    def is_set(self, obj: ReactiveHost) -> bool:
        """Check if this parameter has been set on the given object.

        Args:
            obj: The reactive host instance to check

        Returns:
            True if the parameter has been set, False otherwise

        Example:
            class MyElement(Element):
                capacity = TrackedParam[float]()

                @constraint
                def my_constraint(self) -> highs_linear_expression:
                    if not self.capacity.is_set(self):
                        return self.energy  # A free row until capacity is set
                    return self.energy <= self.capacity

        """
        record_access(obj, self._name)
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


def record_access(obj: ReactiveHost, key: str) -> None:
    """Record that the computation being tracked read ``key`` on ``obj``.

    The key is a parameter name, or ``method:<name>`` for a reactive method.
    Recording the host alongside the key lets a method depend on parameters and
    methods of other objects, such as a node balance reading a connection's flow.
    """
    tracking = tracking_context.get()
    if tracking is not None:
        tracking.add((obj, key))


def register_dependencies(
    obj: ReactiveHost,
    method_name: str,
    deps: set[Dependency],
    previous_deps: set[Dependency],
) -> None:
    """Register ``method_name`` on ``obj`` as a dependent of exactly what it read.

    Each host keeps a reverse index from its keys to the methods that read them,
    so changing a value finds its dependents without scanning every object.
    Keys the method read last time but not this time are removed from the index.
    """
    for host, key in previous_deps - deps:
        _dependents_of(host)[key].discard((obj, method_name))
    for host, key in deps - previous_deps:
        _dependents_of(host).setdefault(key, set()).add((obj, method_name))


def _dependents_of(host: ReactiveHost) -> dict[str, set[tuple[ReactiveHost, str]]]:
    """Return the host's reverse index from its keys to the methods that read them."""
    dependents: dict[str, set[tuple[ReactiveHost, str]]] | None = getattr(host, _DEPENDENTS_ATTR, None)
    if dependents is None:
        dependents = {}
        setattr(host, _DEPENDENTS_ATTR, dependents)
    return dependents


def _invalidate_param_dependents(obj: ReactiveHost, param_name: str) -> None:
    """Invalidate every reactive method, on any object, that depends on a parameter.

    Invalidation propagates through methods that read invalidated methods, so a
    constraint built from another object's derived expression is rebuilt too.

    Args:
        obj: The reactive host instance (Element or Segment)
        param_name: The parameter name that changed

    """
    pending: list[Dependency] = [(obj, param_name)]
    while pending:
        dependency = pending.pop()
        host, key = dependency
        for dependent, method_name in _dependents_of(host).get(key, ()):
            # Every indexed method has state: it is registered after it computes
            state = ensure_decorator_state(dependent, method_name)
            if state["invalidated"]:
                continue
            state["invalidated"] = True
            pending.append((dependent, f"method:{method_name}"))


def get_decorator_state(obj: ReactiveHost, method_name: str) -> DecoratorState | None:
    """Get the state dictionary for a decorator method on an object.

    Args:
        obj: The reactive host instance (Element or Segment)
        method_name: The method name

    Returns:
        State dictionary or None if not yet initialized

    """
    state_attr = f"_reactive_state_{method_name}"
    return getattr(obj, state_attr, None)


def ensure_decorator_state(obj: ReactiveHost, method_name: str) -> DecoratorState:
    """Ensure a state dictionary exists for a decorator method on an object.

    Args:
        obj: The reactive host instance (Element or Segment)
        method_name: The method name

    Returns:
        State dictionary (created if needed)

    """
    state_attr = f"_reactive_state_{method_name}"
    if not hasattr(obj, state_attr):
        setattr(obj, state_attr, {"invalidated": True, "deps": set(), "result": None})
    return getattr(obj, state_attr)


# Re-export tracking context for use by decorators
__all__ = [
    "DecoratorState",
    "Dependency",
    "TrackedParam",
    "ensure_decorator_state",
    "get_decorator_state",
    "record_access",
    "register_dependencies",
    "tracking_context",
]
