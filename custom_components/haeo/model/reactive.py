"""Reactive parameter and constraint caching infrastructure for warm start optimization.

This module provides automatic dependency tracking for model elements, enabling
efficient warm start optimization where only changed constraints are updated.

The pattern is inspired by reactive frameworks like MobX:
- Parameters are declared as TrackedParam descriptors
- Constraint methods are decorated with @cached_constraint
- Dependencies are tracked automatically during first execution
- Parameter changes invalidate only dependent constraints
"""

from collections.abc import Callable, Sequence
from contextvars import ContextVar
from functools import partial
from typing import Any, TypeVar, overload

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression

T = TypeVar("T")

# Context for tracking parameter access during constraint computation
_tracking_context: ContextVar[set[str] | None] = ContextVar("tracking", default=None)


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
        if old is not _UNSET and old != value:
            obj.invalidate_dependents(self._name)


# Sentinel for unset values
class _UnsetType:
    """Sentinel type for unset parameter values."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<UNSET>"


_UNSET = _UnsetType()


class CachedConstraint:
    """Descriptor/decorator that caches constraint expressions with automatic dependency tracking.

    On first call, tracks which TrackedParam values are accessed and caches the result.
    Subsequent calls return cached result unless the constraint was invalidated.

    Usage:
        class Battery(ReactiveElement):
            capacity = TrackedParam[Sequence[float]]()

            @cached_constraint
            def soc_max_constraint(self) -> list[highs_linear_expression]:
                return [self.stored_energy[i] <= self.capacity[i] for i in ...]

    """

    def __init__(self, fn: Callable[..., Any]) -> None:
        """Initialize with the constraint method."""
        self._fn = fn
        self._name: str = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the constraint name."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "CachedConstraint": ...

    @overload
    def __get__(self, obj: "ReactiveElement", objtype: type) -> Callable[[], Any]: ...

    def __get__(
        self, obj: "ReactiveElement | None", objtype: type
    ) -> "CachedConstraint | Callable[[], Any]":
        """Return bound method that uses caching."""
        if obj is None:
            return self
        return partial(self._call, obj)

    def _call(self, obj: "ReactiveElement") -> Any:
        """Execute with caching and dependency tracking."""
        # Return cached if not invalidated
        if obj.has_cached_constraint(self._name) and not obj.is_constraint_invalidated(self._name):
            return obj.get_cached_constraint(self._name)

        # Track parameter access during computation
        tracking: set[str] = set()
        token = _tracking_context.set(tracking)
        try:
            result = self._fn(obj)
        finally:
            _tracking_context.reset(token)

        # Store result and dependencies
        obj.cache_constraint(self._name, result, tracking)

        return result


# Convenient decorator alias
cached_constraint = CachedConstraint


class CachedCost:
    """Descriptor/decorator that caches cost expressions with automatic dependency tracking.

    Similar to CachedConstraint but for objective function contributions.
    """

    def __init__(self, fn: Callable[..., Sequence[highs_linear_expression]]) -> None:
        """Initialize with the cost method."""
        self._fn = fn
        self._name: str = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the cost method name."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "CachedCost": ...

    @overload
    def __get__(
        self, obj: "ReactiveElement", objtype: type
    ) -> Callable[[], Sequence[highs_linear_expression]]: ...

    def __get__(
        self, obj: "ReactiveElement | None", objtype: type
    ) -> "CachedCost | Callable[[], Sequence[highs_linear_expression]]":
        """Return bound method that uses caching."""
        if obj is None:
            return self
        return partial(self._call, obj)

    def _call(self, obj: "ReactiveElement") -> Sequence[highs_linear_expression]:
        """Execute with caching and dependency tracking."""
        # Return cached if not invalidated
        if obj.has_cached_cost(self._name) and not obj.is_cost_invalidated(self._name):
            return obj.get_cached_cost(self._name)

        # Track parameter access during computation
        tracking: set[str] = set()
        token = _tracking_context.set(tracking)
        try:
            result = self._fn(obj)
        finally:
            _tracking_context.reset(token)

        # Store result and dependencies
        obj.cache_cost(self._name, result, tracking)

        return result


# Convenient decorator alias
cached_cost = CachedCost


class ReactiveElement:
    """Mixin providing reactive parameter and constraint caching infrastructure.

    Elements inheriting from this class can use TrackedParam for parameters
    and @cached_constraint for constraint methods. Dependency tracking is automatic.
    """

    def __init__(self) -> None:
        """Initialize reactive infrastructure."""
        super().__init__()
        self._invalidated: set[str] = set()
        self._constraint_cache: dict[str, Any] = {}
        self._constraint_deps: dict[str, set[str]] = {}
        self._applied_constraints: dict[str, highs_cons | list[highs_cons]] = {}
        self._invalidated_costs: set[str] = set()
        self._cost_cache: dict[str, Sequence[highs_linear_expression]] = {}
        self._cost_deps: dict[str, set[str]] = {}

    # Cache access methods for constraints (called by CachedConstraint)

    def has_cached_constraint(self, name: str) -> bool:
        """Check if a constraint is cached."""
        return name in self._constraint_cache

    def is_constraint_invalidated(self, name: str) -> bool:
        """Check if a constraint is invalidated."""
        return name in self._invalidated

    def get_cached_constraint(self, name: str) -> Any:
        """Get a cached constraint."""
        return self._constraint_cache[name]

    def cache_constraint(self, name: str, result: Any, deps: set[str]) -> None:
        """Cache a constraint with its dependencies."""
        self._constraint_cache[name] = result
        self._constraint_deps[name] = deps
        self._invalidated.discard(name)

    # Cache access methods for costs (called by CachedCost)

    def has_cached_cost(self, name: str) -> bool:
        """Check if a cost is cached."""
        return name in self._cost_cache

    def is_cost_invalidated(self, name: str) -> bool:
        """Check if a cost is invalidated."""
        return name in self._invalidated_costs

    def get_cached_cost(self, name: str) -> Sequence[highs_linear_expression]:
        """Get a cached cost."""
        return self._cost_cache[name]

    def cache_cost(self, name: str, result: Sequence[highs_linear_expression], deps: set[str]) -> None:
        """Cache a cost with its dependencies."""
        self._cost_cache[name] = result
        self._cost_deps[name] = deps
        self._invalidated_costs.discard(name)

    # Dependency tracking

    def invalidate_dependents(self, param_name: str) -> None:
        """Mark constraints and costs that depend on the given parameter as needing recomputation.

        Args:
            param_name: The parameter name that changed

        """
        # Invalidate constraints that depend on this parameter
        for constraint_name, deps in self._constraint_deps.items():
            if param_name in deps:
                self._invalidated.add(constraint_name)

        # Invalidate costs that depend on this parameter
        for cost_name, deps in self._cost_deps.items():
            if param_name in deps:
                self._invalidated_costs.add(cost_name)

    # Constraint application methods

    def apply_constraints(self, solver: Highs) -> None:
        """Apply any invalidated constraints to the solver.

        For constraints that haven't been applied yet, adds them to the solver.
        For constraints that exist, updates coefficients and bounds in-place.

        Args:
            solver: The HiGHS solver instance

        """
        # Find all cached_constraint methods on this class
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, CachedConstraint):
                self._apply_single_constraint(solver, name)

    def _apply_single_constraint(self, solver: Highs, constraint_name: str) -> None:
        """Apply a single constraint method to the solver.

        Args:
            solver: The HiGHS solver instance
            constraint_name: Name of the cached_constraint method

        """
        # Get the constraint method and call it (uses cache if valid)
        method = getattr(self, constraint_name)
        expr = method()

        if expr is None:
            return

        existing = self._applied_constraints.get(constraint_name)

        if existing is None:
            # First time: add constraint to solver
            if isinstance(expr, list):
                self._applied_constraints[constraint_name] = solver.addConstrs(expr)
            else:
                self._applied_constraints[constraint_name] = solver.addConstr(expr)
        elif constraint_name in self._invalidated:
            # Update existing constraint(s)
            self._update_constraint(solver, existing, expr)
            self._invalidated.discard(constraint_name)

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

    def apply_costs(self, solver: Highs) -> None:
        """Apply any invalidated cost expressions to the solver.

        For costs that haven't been applied yet, this is handled by minimize().
        For costs that have changed, updates objective coefficients in-place.

        Args:
            solver: The HiGHS solver instance

        """
        # Find all cached_cost methods on this class
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, CachedCost) and name in self._invalidated_costs:
                # Get the cost method and call it (uses cache if valid)
                method = getattr(self, name)
                cost_exprs = method()

                # Update objective coefficients for each expression
                for expr in cost_exprs:
                    for var_idx, coeff in zip(expr.idxs, expr.vals, strict=True):
                        solver.changeColCost(var_idx, coeff)

                self._invalidated_costs.discard(name)
