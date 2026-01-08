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
from typing import TYPE_CHECKING, Any, overload

import numpy as np

if TYPE_CHECKING:
    from highspy import Highs
    from highspy.highs import highs_cons, highs_linear_expression

    from .element import Element

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
    # Get all CachedMethod descriptors on the element's class
    for attr_name in dir(type(element)):
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


class CachedMethod[R]:
    """Base descriptor/decorator that caches method results with automatic dependency tracking.

    On first call, tracks which TrackedParam values are accessed and caches the result.
    Subsequent calls return cached result unless the method was invalidated.

    Subclasses set `kind` to distinguish constraints from costs for reflection-based discovery.
    """

    kind: CachedKind  # Set by subclasses

    def __init__(self, fn: Callable[..., R]) -> None:
        """Initialize with the method."""
        self._fn = fn
        self._name: str = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the method name."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "CachedMethod[R]": ...

    @overload
    def __get__(self, obj: "Element[Any]", objtype: type) -> Callable[[], R]: ...

    def __get__(self, obj: "Element[Any] | None", objtype: type) -> "CachedMethod[R] | Callable[[], R]":
        """Return bound method that uses caching."""
        if obj is None:
            return self
        return partial(self._call, obj)

    def _call(self, obj: "Element[Any]") -> R:
        """Execute with caching and dependency tracking."""
        state = _ensure_decorator_state(obj, self._name)

        # Return cached if not invalidated
        if not state["invalidated"] and state["result"] is not None:
            return state["result"]  # type: ignore[return-value]

        # Track parameter access during computation
        tracking: set[str] = set()
        token = _tracking_context.set(tracking)
        try:
            result = self._fn(obj)
        finally:
            _tracking_context.reset(token)

        # Store result and dependencies
        state["result"] = result
        state["deps"] = tracking
        state["invalidated"] = False

        return result


class CachedConstraint[R](CachedMethod[R]):
    """Decorator that caches constraint expressions with automatic dependency tracking.

    Handles the full constraint lifecycle:
    1. Computes expressions
    2. Creates constraints in solver (first call)
    3. Updates constraints in solver (when invalidated)
    4. Tracks dependencies for invalidation

    Usage:
        class Battery(Element):
            capacity = TrackedParam[Sequence[float]]()

            @constraint
            def soc_max_constraint(self) -> list[highs_linear_expression]:
                return [self.stored_energy[i] <= self.capacity[i] for i in ...]

    """

    kind = CachedKind.CONSTRAINT

    def __init__(self, fn: Callable[..., R], *, output: bool = False) -> None:
        """Initialize constraint decorator.

        Args:
            fn: The constraint function
            output: If True, expose as shadow price output (default False)

        """
        super().__init__(fn)
        self.output = output

    def _call(self, obj: "Element[Any]") -> R:
        """Execute with caching, dependency tracking, and solver lifecycle management."""
        state = _ensure_decorator_state(obj, self._name)

        # Check if we need to recompute
        needs_recompute = state["invalidated"] or "result" not in state
        is_first_call = "constraint" not in state

        if not needs_recompute:
            return state["result"]  # type: ignore[return-value]

        # Track parameter access during computation
        tracking: set[str] = set()
        token = _tracking_context.set(tracking)
        try:
            expr = self._fn(obj)
        finally:
            _tracking_context.reset(token)

        # Store result and dependencies
        state["result"] = expr
        state["deps"] = tracking
        state["invalidated"] = False

        # Handle None result (constraint not applicable)
        if expr is None:
            return expr  # type: ignore[return-value]

        # Get solver from element
        solver: Highs = obj._solver  # noqa: SLF001

        # First call: create constraint(s) in solver
        if is_first_call:
            from highspy.highs import highs_cons

            # Import here to avoid circular dependency
            if isinstance(expr, list):
                cons = solver.addConstrs(expr)
            else:
                cons = solver.addConstr(expr)  # type: ignore[arg-type]
            state["constraint"] = cons
        else:
            # Subsequent call with invalidation: update constraint(s)
            existing = state["constraint"]
            self._update_constraint(solver, existing, expr)  # type: ignore[arg-type]

        return expr  # type: ignore[return-value]

    def _update_constraint(
        self,
        solver: "Highs",
        existing: "highs_cons | list[highs_cons]",
        expr: "highs_linear_expression | list[highs_linear_expression]",
    ) -> None:
        """Update existing constraint(s) with new expression(s).

        Args:
            solver: The HiGHS solver instance
            existing: The existing constraint(s) to update
            expr: The new expression(s)

        """
        if isinstance(existing, list):
            if not isinstance(expr, list):
                msg = "Expression type mismatch: expected list"
                raise TypeError(msg)
            for cons, exp in zip(existing, expr, strict=True):
                self._update_single_constraint(solver, cons, exp)
        else:
            if isinstance(expr, list):
                msg = "Expression type mismatch: expected single expression"
                raise TypeError(msg)
            self._update_single_constraint(solver, existing, expr)

    def _update_single_constraint(
        self,
        solver: "Highs",
        cons: "highs_cons",
        expr: "highs_linear_expression",
    ) -> None:
        """Update a single constraint with new expression.

        Args:
            solver: The HiGHS solver instance
            cons: The existing constraint to update
            expr: The new expression

        """
        # Update bounds if present
        if expr.bounds is not None:
            solver.changeRowBounds(cons.index, expr.bounds[0], expr.bounds[1])

        # Update coefficients
        # Get existing expression to compare
        old_expr = solver.getExpr(cons)
        old_coeffs = dict(zip(old_expr.idxs, old_expr.vals, strict=True))
        new_coeffs = dict(zip(expr.idxs, expr.vals, strict=True))

        # Apply coefficient changes
        all_vars = set(old_coeffs) | set(new_coeffs)
        for var_idx in all_vars:
            old_val = old_coeffs.get(var_idx, 0.0)
            new_val = new_coeffs.get(var_idx, 0.0)
            if old_val != new_val:
                solver.changeCoeff(cons.index, var_idx, new_val)


class CachedCost[R](CachedMethod[R]):
    """Decorator that caches cost expressions with automatic dependency tracking.

    Only handles caching - the objective is rebuilt each optimization via Network.optimize().
    """

    kind = CachedKind.COST


class OutputMethod[R]:
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

    def __init__(self, fn: Callable[..., R]) -> None:
        """Initialize with the method."""
        self._fn = fn
        self._name: str = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the method name."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "OutputMethod[R]": ...

    @overload
    def __get__(self, obj: "Element[Any]", objtype: type) -> Callable[[], R]: ...

    def __get__(self, obj: "Element[Any] | None", objtype: type) -> "OutputMethod[R] | Callable[[], R]":
        """Return bound method."""
        if obj is None:
            return self
        return partial(self._fn, obj)


# Convenient decorator aliases
constraint = CachedConstraint
cost = CachedCost
output = OutputMethod
