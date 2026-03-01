"""Decorator classes for reactive caching of constraints and costs."""

from collections.abc import Callable
from functools import partial
from typing import TypeVar, overload

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression
import numpy as np

from custom_components.haeo.core.model.output_data import ModelOutputValue, OutputData

from .protocols import ReactiveHost
from .tracked_param import ensure_decorator_state, tracking_context

# Type variable for generic return types
R = TypeVar("R")


class ReactiveMethod[R]:
    """Base descriptor/decorator that caches method results with automatic dependency tracking.

    On first call, tracks which TrackedParam values are accessed and caches the result.
    Subsequent calls return cached result unless the method was invalidated.
    """

    def __init__(self, fn: Callable[..., R]) -> None:
        """Initialize with the method."""
        self._fn = fn
        self._name: str = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the method name."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "ReactiveMethod[R]": ...

    @overload
    def __get__(self, obj: "ReactiveHost", objtype: type) -> Callable[[], R]: ...

    def __get__(self, obj: "ReactiveHost | None", objtype: type) -> "ReactiveMethod[R] | Callable[[], R]":
        """Return bound method that uses caching."""
        if obj is None:
            return self
        return partial(self._call, obj)

    def _call(self, obj: "ReactiveHost") -> R:
        """Execute with caching and dependency tracking."""
        state = ensure_decorator_state(obj, self._name)

        # Return cached if not invalidated
        if not state["invalidated"] and state["result"] is not None:
            return state["result"]  # type: ignore[return-value]

        # Track parameter and method access during computation
        tracking: set[str] = set()
        token = tracking_context.set(tracking)
        try:
            result = self._fn(obj)
        finally:
            tracking_context.reset(token)

        # Store result and dependencies
        state["result"] = result
        state["deps"] = tracking
        state["invalidated"] = False

        return result

    def _record_access(self, obj: "ReactiveHost") -> None:  # noqa: ARG002 (obj not used but part of method signature)
        """Record this method's access in the current tracking context.

        When another cached method calls this one, this establishes a dependency.
        """
        tracking = tracking_context.get()
        if tracking is not None:
            # Record as "method:name" to distinguish from param names
            tracking.add(f"method:{self._name}")


class ReactiveConstraint[R](ReactiveMethod[R]):
    """Decorator that caches constraint expressions with automatic dependency tracking.

    Handles the full constraint lifecycle:
    1. Computes expressions
    2. Creates constraints in solver (first call)
    3. Updates constraints in solver (when invalidated)
    4. Tracks dependencies for invalidation

    Usage:
        class Battery(Element):
            capacity = TrackedParam[NDArray[np.floating[Any]]]()

            @constraint(output=True, unit="$/kWh")
            def battery_soc_max(self) -> list[highs_linear_expression]:
                return [self.stored_energy[i] <= self.capacity[i] for i in ...]

    """

    def __init__(self, fn: Callable[..., R], *, output: bool = False, unit: str = "$/kW") -> None:
        """Initialize constraint decorator.

        Args:
            fn: The constraint function
            output: If True, expose as shadow price output (default False)
            unit: Unit for shadow price output (default "$/kW")

        """
        super().__init__(fn)
        self.output = output
        self.unit = unit

    def get_output(self, obj: "ReactiveHost") -> "OutputData | None":
        """Get output data for this constraint (shadow prices if output=True).

        Args:
            obj: The reactive host instance (Element or Segment)

        Returns:
            OutputData with shadow prices, or None if output=False or constraint not yet applied

        """
        if not self.output:
            return None

        # Import here to avoid circular dependency
        from custom_components.haeo.core.model.const import OutputType  # noqa: PLC0415

        # Get the state for this constraint
        state_attr = f"_reactive_state_{self._name}"
        state = getattr(obj, state_attr, None)
        if state is None or "constraint" not in state:
            return None

        # Extract shadow prices from the constraint using the solver
        cons = state["constraint"]
        arr = np.asarray(cons, dtype=object)
        values = tuple(obj._solver.constrDuals(arr).flat)  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]
        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit=self.unit,
            values=values,
        )

    def _call(self, obj: "ReactiveHost") -> R:
        """Execute with caching, dependency tracking, and solver lifecycle management."""
        # Record access if being tracked by another method
        self._record_access(obj)

        state = ensure_decorator_state(obj, self._name)

        # Check if we need to recompute
        needs_recompute = state["invalidated"] or "result" not in state
        is_first_call = "constraint" not in state

        if not needs_recompute:
            return state["result"]  # type: ignore[return-value]

        # Track parameter and method access during computation
        tracking: set[str] = set()
        token = tracking_context.set(tracking)
        try:
            expr = self._fn(obj)
        finally:
            tracking_context.reset(token)

        # Store result and dependencies
        state["result"] = expr
        state["deps"] = tracking
        state["invalidated"] = False

        # Handle None result (constraint not applicable)
        if expr is None:
            return expr  # type: ignore[return-value]

        # Get solver from element
        solver: Highs = obj._solver  # noqa: SLF001 # pyright: ignore[reportPrivateUsage] (tightly coupled reactive infrastructure)

        # First call: create constraint(s) in solver
        if is_first_call:
            cons = solver.addConstrs(expr) if isinstance(expr, list) else solver.addConstr(expr)  # type: ignore[arg-type]
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
            # Both existing and expr are lists - update element-wise
            assert isinstance(expr, list), "Expression type must match existing constraint type"  # noqa: S101
            for cons, exp in zip(existing, expr, strict=True):
                self._update_single_constraint(solver, cons, exp)
        else:
            # Both existing and expr are single values
            assert not isinstance(expr, list), "Expression type must match existing constraint type"  # noqa: S101
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
        # Update bounds (handle both addition and removal of bounds)
        # Get old bounds from the constraint
        old_expr = solver.getExpr(cons)
        old_bounds = old_expr.bounds
        new_bounds = expr.bounds

        # Update bounds if they changed
        if old_bounds != new_bounds:
            if new_bounds is not None:
                solver.changeRowBounds(cons.index, new_bounds[0], new_bounds[1])
            elif old_bounds is not None:
                # Bounds were removed - set to unconstrained (-inf, inf)
                solver.changeRowBounds(cons.index, float("-inf"), float("inf"))

        # Update coefficients
        # Get existing expression to compare
        old_coeffs = dict(zip(old_expr.idxs, old_expr.vals, strict=True))
        new_coeffs = dict(zip(expr.idxs, expr.vals, strict=True))

        # Apply coefficient changes for all variables (old, new, and removed)
        # Variables not in new_coeffs get coefficient 0.0 (effectively removed)
        all_vars = set(old_coeffs) | set(new_coeffs)
        for var_idx in all_vars:
            old_val = old_coeffs.get(var_idx, 0.0)
            new_val = new_coeffs.get(var_idx, 0.0)
            if old_val != new_val:
                solver.changeCoeff(cons.index, var_idx, new_val)


class ReactiveCost[R](ReactiveMethod[R]):
    """Decorator that caches cost expressions with automatic dependency tracking.

    Tracks dependencies on both TrackedParam values and other cached methods.
    When called by another cached method, records access to establish dependency.
    """

    def _call(self, obj: "ReactiveHost") -> R:
        """Execute with caching and dependency tracking."""
        # Record access if being tracked by another method
        self._record_access(obj)

        # Use base class caching with dependency tracking
        return super()._call(obj)


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

    def __init__(self, fn: Callable[..., R], *, output_name: str | None = None) -> None:
        """Initialize with the method."""
        self._fn = fn
        self._name: str = fn.__name__
        self._output_name: str | None = output_name

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the method name."""
        self._name = name
        if self._output_name is None:
            self._output_name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "OutputMethod[R]": ...

    @overload
    def __get__(self, obj: ReactiveHost, objtype: type) -> Callable[[], R]: ...

    def __get__(self, obj: "ReactiveHost | None", objtype: type) -> "OutputMethod[R] | Callable[[], R]":
        """Return bound method."""
        if obj is None:
            return self
        return partial(self._fn, obj)

    @property
    def output_name(self) -> str:
        """Return the output name exposed by this method."""
        return self._output_name or self._name

    def get_output(self, obj: ReactiveHost) -> "ModelOutputValue | None":
        """Get output data for this output method.

        Args:
            obj: The element instance

        Returns:
            OutputData or nested output mapping from calling the method, or None if method returns None

        """
        method = getattr(obj, self._name)
        return method()


# Decorator shortcuts for cleaner syntax
@overload
def constraint[R](fn: Callable[..., R], /) -> ReactiveConstraint[R]: ...


@overload
def constraint(*, output: bool = False, unit: str = "$/kW") -> Callable[[Callable[..., R]], ReactiveConstraint[R]]: ...


def constraint[R](
    fn: Callable[..., R] | None = None, /, *, output: bool = False, unit: str = "$/kW"
) -> ReactiveConstraint[R] | Callable[[Callable[..., R]], ReactiveConstraint[R]]:
    """Decorate constraint methods with automatic caching and dependency tracking.

    Can be used with or without arguments:
    - @constraint - basic constraint
    - @constraint(output=True, unit="$/kWh") - constraint that generates shadow price output

    Args:
        fn: The function to decorate (when used without arguments)
        output: If True, expose as shadow price output (default False)
        unit: Unit for shadow price output (default "$/kW")

    Returns:
        Decorated function or decorator factory

    """
    if fn is not None:
        # Called without arguments: @constraint
        return ReactiveConstraint(fn, output=output, unit=unit)
    # Called with arguments: @constraint(output=True, unit="$/kWh")
    return lambda f: ReactiveConstraint(f, output=output, unit=unit)


cost = ReactiveCost


@overload
def output[R](fn: Callable[..., R], /) -> OutputMethod[R]: ...


@overload
def output(*, name: str) -> Callable[[Callable[..., R]], OutputMethod[R]]: ...


def output[R](
    fn: Callable[..., R] | None = None, /, *, name: str | None = None
) -> OutputMethod[R] | Callable[[Callable[..., R]], OutputMethod[R]]:
    """Decorate methods as outputs, optionally overriding their output name."""
    if fn is not None:
        return OutputMethod(fn, output_name=name)
    return lambda f: OutputMethod(f, output_name=name)
