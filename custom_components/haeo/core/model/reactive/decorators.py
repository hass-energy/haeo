"""Decorator classes for reactive caching of constraints and costs."""

from collections.abc import Callable
from functools import partial
from typing import TypeVar, overload

from highspy import Highs, HighsRanging, HighsSolution
import numpy as np

from custom_components.haeo.core.model.output_data import ModelOutputValue, OutputData
from custom_components.haeo.core.model.util.solver_rows import add_row, add_rows, update_row

from .protocols import ReactiveHost
from .tracked_param import ensure_decorator_state, tracking_context


def _get_ranging(solver: Highs) -> tuple[HighsRanging, HighsSolution]:
    """Get ranging and solution data, caching on the solver instance.

    getRanging() is expensive (full basis factorization) and the result is
    identical for all constraints in the same model.  Cache it on the solver
    so that multiple get_output() calls after one solve share a single
    computation.  Call clear_ranging_cache() after each solve to invalidate.
    """
    cached: tuple[HighsRanging, HighsSolution] | None = getattr(solver, "_haeo_ranging_cache", None)
    if cached is not None:
        return cached

    _status, rng = solver.getRanging()
    sol = solver.getSolution()
    result = (rng, sol)
    solver._haeo_ranging_cache = result  # type: ignore[attr-defined]  # noqa: SLF001 (intentional cache attribute)
    return result


def clear_ranging_cache(solver: Highs) -> None:
    """Clear the cached ranging data after a solve cycle."""
    solver._haeo_ranging_cache = None  # type: ignore[attr-defined]  # noqa: SLF001 (intentional cache attribute)


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
        solver: Highs = obj._solver  # noqa: SLF001 (tightly coupled reactive infrastructure requires solver access) # pyright: ignore[reportPrivateUsage]
        cons = state["constraint"]
        arr = np.asarray(cons, dtype=object)
        values = tuple(solver.constrDuals(arr).flat)

        # Extract ranging (capacity at current shadow price)
        rng, sol = _get_ranging(solver)
        range_up: tuple[float, ...] | None = None
        range_dn: tuple[float, ...] | None = None
        if rng.valid:
            up_vals: list[float] = []
            dn_vals: list[float] = []
            for c_obj in arr.flat:
                idx = c_obj.index
                row_val = sol.row_value[idx]
                up_vals.append(float(rng.row_bound_up.value_[idx] - row_val))
                dn_vals.append(float(row_val - rng.row_bound_dn.value_[idx]))
            range_up = tuple(up_vals)
            range_dn = tuple(dn_vals)

        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit=self.unit,
            values=values,
            range_up=range_up,
            range_dn=range_dn,
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
        solver: Highs = obj._solver  # noqa: SLF001 (tightly coupled reactive infrastructure requires solver access) # pyright: ignore[reportPrivateUsage]

        # First call: create constraint(s) in solver
        if is_first_call:
            cons = add_rows(solver, expr) if isinstance(expr, list) else add_row(solver, expr)  # type: ignore[arg-type]
            state["constraint"] = cons
        else:
            # Subsequent call with invalidation: update constraint(s) from the expression they hold
            existing = state["constraint"]
            applied = state["applied"]
            if isinstance(existing, list):
                for cons, old, new in zip(existing, applied, expr, strict=True):  # type: ignore[arg-type]
                    update_row(solver, cons, old, new)
            else:
                update_row(solver, existing, applied, expr)  # type: ignore[arg-type]
        state["applied"] = expr

        return expr  # type: ignore[return-value]


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
