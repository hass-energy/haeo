"""Decorator classes for reactive caching of constraints and costs."""

from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar, overload

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression
import numpy as np

from custom_components.haeo.core.model.output_data import ModelOutputValue, OutputData
from custom_components.haeo.core.model.util.solver_rows import add_row, add_rows, is_free_row, update_row

from .protocols import ReactiveHost
from .tracked_param import Dependency, ensure_decorator_state, record_access, register_dependencies, tracking_context

# Type variable for generic return types
R = TypeVar("R")


class ReactiveMethod[R]:
    """Descriptor/decorator that caches method results with automatic dependency tracking.

    On first call, tracks which TrackedParam values are accessed and caches the result.
    Subsequent calls return cached result unless the method was invalidated.
    A reactive method that calls this one depends on it, so invalidating this
    method invalidates its callers too.

    Used directly through ``@computed`` for values computed from parameters, such
    as a segment's transformed flow, that constraints and costs build on.
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
        # A method calling this one depends on it
        record_access(obj, f"method:{self._name}")

        state = ensure_decorator_state(obj, self._name)

        # Return cached if not invalidated
        if not state["invalidated"]:
            return state["result"]  # type: ignore[return-value]

        result = self._compute(obj, state)
        state["result"] = result
        return result

    def _compute(self, obj: "ReactiveHost", state: dict[str, Any]) -> R:
        """Run the method, recording and registering everything it reads."""
        tracking: set[Dependency] = set()
        token = tracking_context.set(tracking)
        try:
            result = self._fn(obj)
        finally:
            tracking_context.reset(token)

        register_dependencies(obj, self._name, tracking, state["deps"])
        state["deps"] = tracking
        state["invalidated"] = False
        return result


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

        cons = applied_constraint(obj, self._name)
        if cons is None:
            return None

        # Extract shadow prices from the constraint using the solver
        solver: Highs = obj._solver  # noqa: SLF001 (tightly coupled reactive infrastructure requires solver access) # pyright: ignore[reportPrivateUsage]
        arr = np.asarray(cons, dtype=object)
        values = tuple(solver.constrDuals(arr).flat)

        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit=self.unit,
            values=values,
        )

    def _call(self, obj: "ReactiveHost") -> R:
        """Execute with caching, dependency tracking, and solver lifecycle management."""
        # A method calling this one depends on it
        record_access(obj, f"method:{self._name}")

        state = ensure_decorator_state(obj, self._name)

        # Check if we need to recompute
        if not state["invalidated"]:
            return state["result"]  # type: ignore[return-value]

        expr = self._compute(obj, state)
        if expr is None:
            state["invalidated"] = True
            msg = (
                f"Constraint {self._name} returned None; return free rows for parts that do not apply, "
                "or an empty list for a constraint with no rows"
            )
            raise TypeError(msg)
        solver: Highs = obj._solver  # noqa: SLF001 (tightly coupled reactive infrastructure requires solver access) # pyright: ignore[reportPrivateUsage]

        # Rows are only recorded as applied once the solver has them, so a failed
        # write is retried on the next call instead of being cached as applied.
        try:
            if "constraint" not in state:
                state["constraint"] = add_rows(solver, expr) if isinstance(expr, list) else add_row(solver, expr)  # type: ignore[arg-type]
            else:
                _write_rows(solver, self._name, state, expr)  # type: ignore[arg-type]
        except Exception:
            state["invalidated"] = True
            raise

        state["applied"] = expr
        state["result"] = expr
        return expr


type _RowExpressions = highs_linear_expression | list[highs_linear_expression]


def _write_rows(solver: Highs, name: str, state: dict[str, Any], expr: _RowExpressions) -> None:
    """Update a constraint's existing rows from the expressions they hold to ``expr``.

    A constraint returns the same rows on every call, marking rows that do not
    currently apply as free, so the LP keeps its shape for warm starts.
    """
    existing = state["constraint"]
    applied = state["applied"]
    if isinstance(existing, list):
        if not isinstance(expr, list) or len(expr) != len(existing):
            new_count = len(expr) if isinstance(expr, list) else 1
            msg = (
                f"Constraint {name} returned {new_count} rows after {len(existing)}; "
                "return free rows for parts that do not apply so the row count stays the same"
            )
            raise ValueError(msg)
        for cons, old, new in zip(existing, applied, expr, strict=True):
            update_row(solver, cons, old, new)
    else:
        update_row(solver, existing, applied, expr)  # type: ignore[arg-type]


def applied_constraint(obj: "ReactiveHost", name: str) -> "highs_cons | list[highs_cons] | None":
    """Return a constraint's rows if any of them currently binds, otherwise None.

    A constraint whose rows are all free is in the LP but does not apply, so it has
    no shadow price and is not listed as a constraint.
    """
    state = getattr(obj, f"_reactive_state_{name}", None)
    if state is None or "constraint" not in state:
        return None
    applied = state["applied"]
    rows = applied if isinstance(applied, list) else [applied]
    if all(is_free_row(row) for row in rows):
        return None
    return state["constraint"]


class ReactiveCost[R](ReactiveMethod[R]):
    """Decorator that caches cost expressions with automatic dependency tracking.

    Tracks dependencies on both TrackedParam values and other cached methods.
    When called by another cached method, records access to establish dependency.
    """


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
computed = ReactiveMethod


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
