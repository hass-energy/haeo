"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .output_data import OutputData
from .reactive import CachedKind, CachedMethod, OutputMethod, TrackedParam

if TYPE_CHECKING:
    from .elements.connection import Connection


class Element[OutputNameT: str]:
    """Base class for electrical entities in energy system modeling.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (periods): hours (variable-width intervals)
    - Price: $/kWh

    This class integrates reactive parameter and constraint caching infrastructure.
    Elements can use TrackedParam for parameters and @constraint/@cost for methods.
    Dependency tracking is automatic.
    """

    def __init__(self, name: str, periods: Sequence[float], *, solver: Highs) -> None:
        """Initialize an element.

        Args:
            name: Name of the entity
            periods: Sequence of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints

        """
        self.name = name
        self.periods = np.asarray(periods)
        self._solver = solver

        # Track connections for power balance
        self._connections: list[tuple[Connection[Any], Literal["source", "target"]]] = []

        # Reactive infrastructure
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

    def __getitem__(self, key: str) -> Any:
        """Get a TrackedParam value by name.

        Args:
            key: Name of the TrackedParam

        Returns:
            The current value of the parameter

        Raises:
            KeyError: If no TrackedParam with this name exists

        """
        # Look up the descriptor on the class
        descriptor = getattr(type(self), key, None)
        if not isinstance(descriptor, TrackedParam):
            msg = f"{type(self).__name__!r} has no TrackedParam {key!r}"
            raise KeyError(msg)
        # Use normal attribute access to trigger the descriptor
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a TrackedParam value by name.

        Setting a value triggers invalidation of dependent constraints/costs.

        Args:
            key: Name of the TrackedParam
            value: New value to set

        Raises:
            KeyError: If no TrackedParam with this name exists

        """
        # Look up the descriptor on the class
        descriptor = getattr(type(self), key, None)
        if not isinstance(descriptor, TrackedParam):
            msg = f"{type(self).__name__!r} has no TrackedParam {key!r}"
            raise KeyError(msg)
        # Use normal attribute access to trigger the descriptor
        setattr(self, key, value)

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def register_connection(self, connection: "Connection[Any]", end: Literal["source", "target"]) -> None:
        """Register a connection to this element.

        Args:
            connection: The connection object
            end: Whether this element is the 'source' or 'target' of the connection

        """
        self._connections.append((connection, end))

    def connection_power(self) -> HighspyArray | NDArray[Any]:
        """Return the net power from connections for all time periods.

        Positive means power flowing into this element from connections.
        Negative means power flowing out of this element to connections.

        Returns:
            Array of connection powers for each time period (HiGHS array or numpy array of expressions)

        """
        if not self._connections:
            # No connections - create zero-valued variables for all periods
            # This ensures comparisons work properly with addConstrs
            return self._solver.addVariables(
                self.n_periods, lb=0, ub=0, name_prefix=f"{self.name}_no_conn_", out_array=True
            )

        # Accumulate power flows from all connections
        total_power: HighspyArray | NDArray[Any] = np.zeros(self.n_periods, dtype=object)

        for conn, end in self._connections:
            if end == "source":
                # Power flowing into this element (as source)
                total_power = total_power + conn.power_into_source
            elif end == "target":
                # Power flowing into this element (as target)
                total_power = total_power + conn.power_into_target

        return total_power

    def extract_values(
        self, sequence: Sequence[Any] | HighspyArray | NDArray[Any] | highs_cons | None
    ) -> tuple[float, ...]:
        """Convert a sequence of HiGHS types to resolved values."""
        if sequence is None:
            return ()

        # Convert to numpy array for batch processing
        arr = np.asarray(sequence, dtype=object)

        # Check first item to determine type and use batch methods
        first_item = arr.flat[0]
        if isinstance(first_item, highs_cons):
            # Use batch constraint dual extraction
            return tuple(self._solver.constrDuals(arr).flat)

        # Default: use batch value extraction (handles highs_var and highs_linear_expression)
        return tuple(self._solver.vals(arr).flat)

    def outputs(self) -> Mapping[OutputNameT, OutputData]:
        """Return output specifications for the element.

        Discovers all @output decorated methods via reflection and calls them.
        The method name is used as the output name (dictionary key).
        """
        result: dict[OutputNameT, OutputData] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, OutputMethod):
                method = getattr(self, name)
                output_data = method()
                if output_data is not None:
                    result[name] = output_data  # type: ignore[literal-required]
        return result

    # Reactive infrastructure methods (merged from ReactiveElement)

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

    def invalidate_dependents(self, param_name: str) -> None:
        """Mark methods that depend on the given parameter as needing recomputation.

        Args:
            param_name: The parameter name that changed

        """
        for kind in CachedKind:
            for method_name, deps in self._deps[kind].items():
                if param_name in deps:
                    self._invalidated[kind].add(method_name)

    def apply_constraints(self) -> None:
        """Apply any invalidated constraints to the solver.

        For constraints that haven't been applied yet, adds them to the solver.
        For constraints that exist, updates coefficients and bounds in-place.
        """
        # Find all constraint methods on this class
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, CachedMethod) and attr.kind == CachedKind.CONSTRAINT:
                self._apply_single_constraint(self._solver, name)

    def _apply_single_constraint(self, solver: Highs, constraint_name: str) -> None:
        """Apply a single constraint method to the solver.

        The constraint method returns a constraint expression (or list of expressions).
        This method calls solver.addConstr() or solver.addConstrs() on the expression.

        Args:
            solver: The HiGHS solver instance
            constraint_name: Name of the constraint method

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

        # Get the constraint method and call it (returns expression(s))
        method = getattr(self, constraint_name)
        expr = method()

        if expr is None:
            return

        # Add constraint(s) to solver and store the result
        result = solver.addConstrs(expr) if isinstance(expr, list) else solver.addConstr(expr)

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
        """
        # Find all cost methods on this class
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
