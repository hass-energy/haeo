"""Reactive parameter and constraint caching infrastructure for warm start optimization.

This module provides automatic dependency tracking for model elements, enabling
efficient warm start optimization where only changed constraints are updated.

The pattern is inspired by reactive frameworks like MobX:
- Parameters are declared as TrackedParam descriptors
- Constraint methods are decorated with @cached_constraint
- Dependencies are tracked automatically during first execution
- Parameter changes invalidate only dependent constraints
"""

from collections.abc import Callable
from contextvars import ContextVar
from enum import Enum, auto
from functools import partial
from typing import Any, TypeVar, overload

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression
import numpy as np

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

            @cached_constraint
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
    def __get__(self, obj: "ReactiveElement", objtype: type) -> T: ...

    def __get__(self, obj: "ReactiveElement | None", objtype: type) -> "TrackedParam[T] | T":
        """Get the parameter value and record access if tracking is active."""
        if obj is None:
            return self
        # Record access if tracking is active
        tracking = _tracking_context.get()
        if tracking is not None:
            tracking.add(self._name)
        return getattr(obj, self._private)

    def __set__(self, obj: "ReactiveElement", value: T) -> None:
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
    def __get__(self, obj: "ReactiveElement", objtype: type) -> Callable[[], Any]: ...

    def __get__(self, obj: "ReactiveElement | None", objtype: type) -> "CachedMethod | Callable[[], Any]":
        """Return bound method that uses caching."""
        if obj is None:
            return self
        return partial(self._call, obj)

    def _call(self, obj: "ReactiveElement") -> Any:
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

            @cached_constraint
            def soc_max_constraint(self) -> list[highs_linear_expression]:
                return [self.stored_energy[i] <= self.capacity[i] for i in ...]

    """

    kind = CachedKind.CONSTRAINT


class CachedCost(CachedMethod):
    """Decorator that caches cost expressions with automatic dependency tracking."""

    kind = CachedKind.COST


# Convenient decorator aliases
cached_constraint = CachedConstraint
cached_cost = CachedCost


class ReactiveElement:
    """Mixin providing reactive parameter and constraint caching infrastructure.

    Elements inheriting from this class can use TrackedParam for parameters
    and @cached_constraint/@cached_cost for methods. Dependency tracking is automatic.
    """

    def __init__(self) -> None:
        """Initialize reactive infrastructure."""
        super().__init__()
        # Unified cache storage indexed by kind
        self._cache: dict[CachedKind, dict[str, Any]] = {
            CachedKind.CONSTRAINT: {},
            CachedKind.COST: {},
        }
        self._deps: dict[CachedKind, dict[str, set[str]]] = {
            CachedKind.CONSTRAINT: {},
            CachedKind.COST: {},
        }
        self._invalidated: dict[CachedKind, set[str]] = {
            CachedKind.CONSTRAINT: set(),
            CachedKind.COST: set(),
        }
        self._applied_constraints: dict[str, highs_cons | list[highs_cons]] = {}
        self._applied_costs: dict[str, highs_linear_expression | list[highs_linear_expression] | None] = {}

    # Unified cache access methods (called by CachedMethod)

    def has_cached(self, kind: CachedKind, name: str) -> bool:
        """Check if a method result is cached."""
        return name in self._cache[kind]

    def is_invalidated(self, kind: CachedKind, name: str) -> bool:
        """Check if a method result is invalidated."""
        return name in self._invalidated[kind]

    def get_cached(self, kind: CachedKind, name: str) -> Any:
        """Get a cached result."""
        return self._cache[kind][name]

    def set_cached(self, kind: CachedKind, name: str, result: Any, deps: set[str]) -> None:
        """Cache a result with its dependencies."""
        self._cache[kind][name] = result
        self._deps[kind][name] = deps
        self._invalidated[kind].discard(name)

    # Dependency tracking

    def invalidate_dependents(self, param_name: str) -> None:
        """Mark methods that depend on the given parameter as needing recomputation.

        Args:
            param_name: The parameter name that changed

        """
        for kind in CachedKind:
            for method_name, deps in self._deps[kind].items():
                if param_name in deps:
                    self._invalidated[kind].add(method_name)

    # Constraint application methods

    def apply_constraints(self) -> None:
        """Apply any invalidated constraints to the solver.

        For constraints that haven't been applied yet, adds them to the solver.
        For constraints that exist, updates coefficients and bounds in-place.

        Requires self._solver to be set (typically by Element.__init__).
        """
        solver = self._solver  # type: ignore[attr-defined]
        # Find all cached_constraint methods on this class
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, CachedMethod) and attr.kind == CachedKind.CONSTRAINT:
                self._apply_single_constraint(solver, name)

    def _apply_single_constraint(self, solver: Highs, constraint_name: str) -> None:
        """Apply a single constraint method to the solver.

        The constraint method is responsible for calling solver.addConstr() or
        solver.addConstrs() and returning the resulting highs_cons object(s).

        Args:
            solver: The HiGHS solver instance
            constraint_name: Name of the cached_constraint method

        """
        # Check if already applied and not invalidated
        is_invalidated = constraint_name in self._invalidated[CachedKind.CONSTRAINT]
        existing = self._applied_constraints.get(constraint_name)
        if existing is not None and not is_invalidated:
            return

        # If invalidated and we have existing constraints, delete them before rebuilding
        if existing is not None and is_invalidated:
            self._delete_constraints(solver, existing)
            del self._applied_constraints[constraint_name]

        # Get the constraint method and call it (adds constraint to solver and returns highs_cons)
        method = getattr(self, constraint_name)
        result = method()

        if result is None:
            return

        # Store the constraint(s) - the method already added them to the solver
        self._applied_constraints[constraint_name] = result
        self._invalidated[CachedKind.CONSTRAINT].discard(constraint_name)

    def _delete_constraints(
        self,
        solver: Highs,
        constraints: highs_cons | list[highs_cons],
    ) -> None:
        """Delete constraint(s) from the solver.

        Args:
            solver: The HiGHS solver instance
            constraints: The constraint(s) to delete

        """
        if isinstance(constraints, list):
            indices = [cons.index for cons in constraints]
            if indices:
                solver.deleteRows(len(indices), indices)
        else:
            solver.deleteRows(1, [constraints.index])

    def _update_constraint(
        self,
        solver: Highs,
        existing: highs_cons | list[highs_cons],
        expr: highs_linear_expression | list[highs_linear_expression],
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
        solver: Highs,
        cons: highs_cons,
        expr: highs_linear_expression,
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

    def apply_costs(self) -> None:
        """Apply any invalidated cost expressions.

        Evaluates cost methods and stores results in _applied_costs.
        The Network.optimize() method collects these and sets the objective.

        Requires self._solver to be set (typically by Element.__init__).
        """
        # Find all cached_cost methods on this class
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            # Check if we need to recompute
            if (
                isinstance(attr, CachedMethod)
                and attr.kind == CachedKind.COST
                and (name not in self._applied_costs or name in self._invalidated[CachedKind.COST])
            ):
                # Get the cost method and call it (uses cache if valid)
                method = getattr(self, name)
                cost_value = method()
                self._applied_costs[name] = cost_value
                self._invalidated[CachedKind.COST].discard(name)
