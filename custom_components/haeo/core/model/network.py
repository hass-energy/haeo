"""Network class for electrical system modeling and optimization."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
import logging
import math
from typing import (
    Any,  # noqa: TID251  # Element is invariant in its output-name Literal (see outputs()'s
    # Mapping[OutputNameT, ...] return), so a plain dict of heterogeneous concrete Element
    # subtypes (Battery, Node, Connection, ...) cannot be typed Element[str] or a shared TypeVar;
    # add()'s @overloads already give callers the precise concrete return type per element_type
    Final,
    Literal,
    overload,
)

from highspy import Highs, HighsModelStatus
import numpy as np
from numpy.typing import NDArray

from .element import Element, NetworkElement
from .elements import ELEMENTS, ModelElementConfig
from .elements.battery import Battery, BatteryElementConfig
from .elements.buffer import Buffer, BufferElementConfig
from .elements.connection import Connection, ConnectionElementConfig, ConnectionOutputName
from .elements.deferrable_load import DeferrableLoad, DeferrableLoadElementConfig
from .elements.node import Node, NodeElementConfig
from .elements.policy_pricing import PolicyPricing, PolicyPricingElementConfig
from .infeasibility import InfeasibleError, Relaxation, RowLabel, conflicting_rows, listing, row_labels, solve_relaxed
from .limits import SELF_CONSUMPTION, LimitRecommendation, Priority
from .limits import recommend_limits as recommend_connection_limits
from .linear import LinearArray, total
from .solver import Solver
from .util.solver_rows import RowIndices

_LOGGER = logging.getLogger(__name__)


OnOffChoose = Literal["on", "off", "choose"]


class SolverError(ValueError):
    """The solver stopped without a plan for a reason other than infeasibility.

    The status is HiGHS's name for how the solve ended, such as ``Unbounded``.
    """

    def __init__(self, status: str) -> None:
        """Record the solver status the solve ended with."""
        super().__init__(f"Optimization failed with status: {status}")
        self.status = status


# Calibration search bounds in log10 space.  The secondary objective can
# be many orders of magnitude larger than the primary, so we need a wide
# range.  1e-12 is effectively zero influence; 1e-1 would dominate.
_CAL_LOG_LO: Final = -12.0
_CAL_LOG_HI: Final = -1.0
_CAL_MAX_STEPS: Final = 40  # bisection budget for upper boundary search
_CAL_CONVERGENCE: Final = 0.01  # stop bisection when interval < this (log10 decades)
_CAL_MARGIN: Final = 0.25  # step back from upper boundary (log10 decades)

# A reduced cost smaller than this, HiGHS's default dual feasibility tolerance, is
# treated as zero when checking a blended plan at its basis
_REDUCED_COST_TOLERANCE: Final = 1e-7
# A value within this of a bound is treated as at that bound
_BOUND_TOLERANCE: Final = 1e-9
# Factor the blend weight moves by until a weight is known on each side. Half a
# decade is about as wide as the narrowest range of working weights seen, so one
# step from just outside it usually lands inside.
_WEIGHT_STEP: Final = 10.0**0.5
# Narrowest gap between a weight too small for the order and one too large for
# the cost that is still searched
_WEIGHT_RESOLUTION: Final = 10.0**0.25
# Smallest blend weight tried when lowering it for the cost
_MIN_BLEND_WEIGHT: Final = 10.0**_CAL_LOG_LO
# Largest blend weight tried when raising it for the order
_MAX_BLEND_WEIGHT: Final = 10.0**_CAL_LOG_HI
# HiGHS's default simplex iteration limit, restored after the optimality check
_UNLIMITED_ITERATIONS: Final = 2**31 - 1


@dataclass(frozen=True, kw_only=True)
class SolveOptions:
    """HiGHS simplex solver options.

    simplex_strategy: 1=dual, 4=primal. Primal is ~25-30% faster on cold starts.
    simplex_scale_strategy: 0=off, 1=basic, 2=equilibration, 3=forced.
    feasibility_tolerance: primal and dual feasibility tolerance. Blended solves
    weight the secondary objective small enough to keep the cost exact, so the
    secondary's reduced costs must still register against this tolerance; at the
    HiGHS default of 1e-7 they can fall below it and leave ties unresolved.
    time_limit: seconds one solve may take before HiGHS stops it, so a solve that
    never finishes cannot hold the optimization up for good.
    """

    presolve: OnOffChoose = "choose"
    parallel: OnOffChoose = "choose"
    simplex_strategy: int = 4
    simplex_scale_strategy: int = 0
    feasibility_tolerance: float = 1e-9
    time_limit: float = 60.0

    def apply(self, h: Solver) -> None:
        """Apply the options to a solver."""
        h.setOptionValue("solver", "simplex")
        h.setOptionValue("presolve", self.presolve)
        h.setOptionValue("parallel", self.parallel)
        h.setOptionValue("simplex_strategy", self.simplex_strategy)
        h.setOptionValue("simplex_scale_strategy", self.simplex_scale_strategy)
        h.setOptionValue("primal_feasibility_tolerance", self.feasibility_tolerance)
        h.setOptionValue("dual_feasibility_tolerance", self.feasibility_tolerance)
        h.time_limit = self.time_limit


@dataclass(frozen=True, slots=True)
class Objective:
    """A linear objective as a dense cost per column and a constant offset.

    Dense costs switch the objective in a single ``changeColsCost`` call
    instead of the expression-based ``setObjective``, which zeros all columns
    then sets non-zero ones (two FFI round-trips per objective switch).
    """

    costs: NDArray[np.float64]
    offset: float

    @classmethod
    def of(cls, expr: LinearArray, n_columns: int) -> "Objective":
        """Return the objective that sums every row of an expression."""
        return cls(expr.column_coefficients(n_columns), float(expr.constant.sum()))

    def value(self, column_values: NDArray[np.float64]) -> float:
        """Return the objective's value at the given column values."""
        return float(self.costs @ column_values) + self.offset


@dataclass(frozen=True, slots=True)
class Objectives:
    """The cost the plan minimizes, and the secondary objective that breaks ties between equally cheap plans."""

    cost: Objective
    secondary: Objective

    @classmethod
    def of(cls, cost: LinearArray, secondary: LinearArray, n_columns: int) -> "Objectives":
        """Return the dense objectives of the cost and secondary expressions."""
        return cls(Objective.of(cost, n_columns), Objective.of(secondary, n_columns))

    def blend(self, weight: float) -> Objective:
        """Return the cost plus ``weight`` times the secondary."""
        return Objective(
            self.cost.costs + weight * self.secondary.costs, self.cost.offset + weight * self.secondary.offset
        )


class Network:
    """Network class for electrical system modeling.

    All values use kW-based units for numerical stability:
    - Power: kW
    - Energy: kWh
    - Time: hours (variable-width intervals)
    - Price: $/kWh

    Note: Periods should be provided in hours (conversion from seconds
    happens at the data loading boundary layer).
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        options: SolveOptions | None = None,
        relax_infeasible: bool = False,
    ) -> None:
        """Create a network with the given period durations and solver options.

        With ``relax_infeasible``, a model whose constraints cannot all hold is
        solved with the fewest of them relaxed, instead of raising.
        """
        self.name = name
        self.periods = np.asarray(periods, dtype=float)
        self.elements: dict[str, Element[Any]] = {}
        self.options = options or SolveOptions()
        self.relax_infeasible = relax_infeasible
        # Rows that could not all hold in the last solve, empty unless it was infeasible
        self.conflicts: tuple[RowLabel, ...] = ()
        # Rows the last plan moved past their bounds, empty unless it was relaxed
        self.relaxations: tuple[Relaxation, ...] = ()
        self._solver = Solver()
        # Weight the last blended solve settled on, where the next one starts
        self._blend_weight: float | None = None

        # Redirect HiGHS logging to Python logger at debug level
        self._solver.cbLogging += self._log_callback

        # Disable console output since we're capturing via callback
        output_off = False
        self._solver.setOptionValue("output_flag", output_off)
        self._solver.setOptionValue("log_to_console", output_off)

        # Apply tunable solver options
        self.options.apply(self._solver)

    @staticmethod
    def _log_callback(_log_type: int, message: str) -> None:
        """Log HiGHS messages to Python logger."""
        if message:
            _LOGGER.debug("HiGHS: %s", message.rstrip())

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def update_periods(self, new_periods: NDArray[np.float64]) -> None:
        """Update period durations across the network.

        Propagates the new periods to all elements and their segments,
        triggering reactive invalidation of dependent constraints and costs.

        Args:
            new_periods: New array of time period durations in hours

        """
        self.periods = np.asarray(new_periods, dtype=float)

        for element in self.elements.values():
            element.update_periods(self.periods)

    @overload
    def add(self, element_config: BatteryElementConfig) -> Battery: ...

    @overload
    def add(self, element_config: DeferrableLoadElementConfig) -> DeferrableLoad: ...

    @overload
    def add(self, element_config: NodeElementConfig) -> Node: ...

    @overload
    def add(self, element_config: ConnectionElementConfig) -> Connection[ConnectionOutputName]: ...

    @overload
    def add(self, element_config: PolicyPricingElementConfig) -> PolicyPricing: ...

    @overload
    def add(self, element_config: BufferElementConfig) -> Buffer: ...

    def add(self, element_config: ModelElementConfig) -> Element[Any]:
        """Add a new element to the network.

        Creates the element and registers connections. For parameter updates,
        modify the element's TrackedParam attributes directly - this will
        automatically invalidate dependent constraints for the next optimization.

        Elements that refer to others by name, such as a buffer's batteries or a
        policy price's connections, resolve them from the elements already added.

        Args:
            element_config: Typed model element configuration dictionary

        Returns:
            The created element

        """
        name = element_config["name"]
        spec = ELEMENTS[element_config["element_type"]]
        # The spec registered for a config's element type is the one built for that config
        arguments = spec.arguments(element_config, self.elements)  # type: ignore[arg-type]  # (spec matches config type)
        element_instance: Element[Any] = spec.factory(name=name, periods=self.periods, solver=self._solver, **arguments)
        self.elements[name] = element_instance

        # Register connections immediately when adding Connection elements
        if isinstance(element_instance, Connection):
            # Get source and target elements (must be NetworkElements for power balance)
            source_element = self.elements.get(element_instance.source)
            target_element = self.elements.get(element_instance.target)

            if not isinstance(source_element, NetworkElement):
                msg = f"Source element '{element_instance.source}' is not a network participant"
                raise ValueError(msg)  # noqa: TRY004 (ValueError is appropriate here, not TypeError)

            if not isinstance(target_element, NetworkElement):
                msg = f"Target element '{element_instance.target}' is not a network participant"
                raise ValueError(msg)  # noqa: TRY004 (ValueError is appropriate here, not TypeError)

            source_element.register_connection(element_instance, "source")
            target_element.register_connection(element_instance, "target")
            element_instance.set_endpoints(source_element, target_element)

        return element_instance

    def cost(self) -> tuple[LinearArray | None, LinearArray | None]:
        """Aggregate the (primary, secondary) costs of all elements, each None when no element has one."""
        primary = total(element.cost() for element in self.elements.values())
        secondary = total(element.secondary_cost() for element in self.elements.values())
        return (primary, secondary)

    def optimize(self) -> float:
        """Solve the optimization problem and return the primary objective value.

        The plan has the lowest cost and, among equally cheap plans, the lowest
        secondary objective. Both come from one blended solve of primary + weight *
        secondary, checked and re-solved with another weight if it fails. The first
        call calibrates the starting weight.
        """
        h = self._solver

        # Assign deterministic priorities to connections based on sorted properties
        connections = sorted(
            (e for e in self.elements.values() if isinstance(e, Connection)),
            key=lambda c: c.sort_key,
        )
        for i, conn in enumerate(connections):
            conn.priority = i

        for element_name, element in self.elements.items():
            try:
                element.constraints()
            except Exception as e:
                msg = f"Failed to apply constraints for element '{element_name}'"
                raise ValueError(msg) from e

        primary, secondary = self.cost()
        if primary is None:
            msg = "Network has no primary cost — add pricing to connections or nodes"
            raise ValueError(msg)
        if secondary is None:
            msg = "Network has no secondary cost — connections must generate time-preference objectives"
            raise ValueError(msg)

        n_vars = h.numVariables
        all_col_indices = np.arange(n_vars, dtype=np.int32)
        objectives = Objectives.of(primary, secondary, n_vars)

        self.conflicts = ()
        self.relaxations = ()
        try:
            return self._solve(all_col_indices, objectives)
        except InfeasibleError:
            balance_rows = {
                row
                for element in self.elements.values()
                if isinstance(element, NetworkElement) and (rows := element.balance_rows()) is not None
                for row in rows.tolist()
            }
            labels = row_labels(self.constraints(), self.n_periods, balance_rows)
            self.conflicts = conflicting_rows(h, labels)
            if not self.relax_infeasible:
                raise InfeasibleError(self.conflicts) from None

        relaxed = solve_relaxed(h, labels, partial(self._solve, all_col_indices, objectives))
        if relaxed is None:
            raise InfeasibleError(self.conflicts)
        cost, self.relaxations = relaxed
        _LOGGER.debug("Relaxed constraints to find a plan: %s", listing(map(str, self.relaxations)))
        return cost

    def _solve(self, all_col_indices: NDArray[np.int32], objectives: Objectives) -> float:
        """Solve the blended objective, calibrating its weight on the first solve."""
        if self._blend_weight is None:
            self._blend_weight = self._calibrate_blend_weight(all_col_indices, objectives)
        return self._solve_blended(all_col_indices, objectives, self._blend_weight)

    def _solve_blended(
        self,
        all_col_indices: NDArray[np.int32],
        objectives: Objectives,
        weight: float,
    ) -> float:
        """Solve primary + weight * secondary, moving the weight until the plan is cost-optimal and then in order.

        Only the weight settled on is kept, since which weights fail depends on the inputs.
        """
        h = self._solver
        h.clearLinearObjectives()
        search = BlendWeightSearch()
        next_weight: float | None = weight
        plan_cost, cost_optimal, order_optimal = 0.0, False, True
        while next_weight is not None:
            weight = next_weight
            plan_cost, cost_optimal, order_optimal = self._solve_at(all_col_indices, objectives, weight)
            next_weight = search.next_weight(weight, cost_optimal=cost_optimal, order_optimal=order_optimal)
            if next_weight is not None:
                _LOGGER.debug("Blended plan at weight %.2e needs another solve; trying %.2e", weight, next_weight)

        if not cost_optimal:
            # Keep the previous weight, and take the cheapest plan without the order
            _LOGGER.warning("No blend weight gives a cost-optimal plan; solving for the cost alone")
            _set_objective(h, all_col_indices, objectives.cost)
            h.run()
            return _ensure_optimal(h)

        if not order_optimal:
            _LOGGER.debug("No blend weight puts the plan in order; keeping the cost-optimal plan at %.2e", weight)
        self._blend_weight = weight
        return plan_cost

    def _solve_at(
        self,
        all_col_indices: NDArray[np.int32],
        objectives: Objectives,
        weight: float,
    ) -> tuple[float, bool, bool]:
        """Solve primary + weight * secondary, and return the plan's cost, whether it is cost-optimal, and in order.

        The cost is priced at the plan's basis with no simplex iterations, which leaves
        the plan where it is and its cost duals for the shadow prices. Reduced costs at
        a fixed basis are linear in the objective, so the secondary's are the blended
        ones minus the cost's, over the weight. The plan is in order when no move that
        leaves the cost unchanged lowers the secondary. Rows count as variables too,
        with their activity as the value. A solve that finds the model infeasible,
        for the cost alone too, raises. Any other failure counts as not
        cost-optimal, so the weight is lowered.
        """
        h = self._solver
        _set_objective(h, all_col_indices, objectives.blend(weight))
        h.run()
        status = h.getModelStatus()
        if status == HighsModelStatus.kUnboundedOrInfeasible:
            status = _status_without_presolve(h)
        if status == HighsModelStatus.kTimeLimit:
            # Another weight would only take as long again
            raise SolverError(h.modelStatusToString(status))
        if status == HighsModelStatus.kInfeasible:
            if _infeasible_for_cost(h, all_col_indices, objectives.cost):
                # Infeasibility does not depend on the objective, so no other weight can help
                raise InfeasibleError
            return math.nan, False, True
        if status != HighsModelStatus.kOptimal:
            return math.nan, False, True
        plan_cost = objectives.cost.value(h.column_values())
        solution = h.getSolution()
        blended = np.concatenate([solution.col_dual, solution.row_dual])

        _set_objective(h, all_col_indices, objectives.cost)
        h.setOptionValue("simplex_iteration_limit", 0)
        try:
            h.run()
        finally:
            h.setOptionValue("simplex_iteration_limit", _UNLIMITED_ITERATIONS)
        cost_optimal = h.getInfo().max_dual_infeasibility <= _REDUCED_COST_TOLERANCE

        solution = h.getSolution()
        cost = np.concatenate([solution.col_dual, solution.row_dual])
        secondary = (blended - cost) / weight

        # Only moves free in cost but not in the secondary can lower it, so only their values and bounds are read
        moves = np.flatnonzero(
            (np.abs(cost) <= _REDUCED_COST_TOLERANCE) & (np.abs(secondary) > _REDUCED_COST_TOLERANCE)
        )
        value = np.concatenate([solution.col_value, solution.row_value])[moves]
        lower, upper = _bounds(h, len(all_col_indices), moves)
        # A move lowers the secondary by raising a variable below its upper bound, or lowering one above its lower bound
        rises = (secondary[moves] < -_REDUCED_COST_TOLERANCE) & (value < upper - _BOUND_TOLERANCE)
        falls = (secondary[moves] > _REDUCED_COST_TOLERANCE) & (value > lower + _BOUND_TOLERANCE)
        return plan_cost, cost_optimal, not (rises | falls).any()

    def _calibrate_blend_weight(
        self,
        all_col_indices: NDArray[np.int32],
        objectives: Objectives,
    ) -> float:
        """Return a weight ``_CAL_MARGIN`` decades below the largest whose plan is cost-optimal.

        The largest weight lets the secondary register most widely, and the margin
        leaves room for later inputs to move the edge before another solve is needed.
        """
        lo, hi = _CAL_LOG_LO, _CAL_LOG_HI

        def _cost_optimal(log_w: float) -> bool:
            return self._solve_at(all_col_indices, objectives, 10.0**log_w)[1]

        if _cost_optimal(hi):
            upper = hi
        elif _cost_optimal(lo):
            upper = _bisect_boundary(lo, hi, _cost_optimal, max_steps=_CAL_MAX_STEPS, convergence=_CAL_CONVERGENCE)
        else:
            _LOGGER.warning("Calibration: no blend weight gives a cost-optimal plan; using %.2e", 10.0**lo)
            return 10.0**lo

        weight = 10.0 ** max(lo, upper - _CAL_MARGIN)
        _LOGGER.debug("Calibrated blend weight: %.2e", weight)
        return weight

    def recommend_limits(self, priority: Priority = SELF_CONSUMPTION) -> dict[str, LimitRecommendation]:
        """Return the recommended first-period hardware limit of each connection with a power limit.

        Read from the plan's basis after ``optimize``, without changing the solver.
        """
        connections = [e for e in self.elements.values() if isinstance(e, Connection)]
        return recommend_connection_limits(self._solver, connections, self.elements, float(self.periods[0]), priority)

    def constraints(self) -> dict[str, dict[str, RowIndices]]:
        """Return all constraints from all elements in the network.

        Returns:
            Dictionary mapping element names to their constraint dictionaries.
            Each constraint dictionary maps constraint method names to constraint objects.

        """
        result: dict[str, dict[str, RowIndices]] = {}
        for element_name, element in self.elements.items():
            if element_constraints := element.constraints():
                result[element_name] = element_constraints
        return result


def _bisect_boundary(
    lo: float,
    hi: float,
    predicate: Callable[[float], bool],
    *,
    max_steps: int,
    convergence: float,
) -> float:
    """Binary search for boundary where predicate changes from True to False.

    Assumes predicate(lo) is True and predicate(hi) is False.
    Returns the highest value where predicate holds.
    """
    for _ in range(max_steps):
        if hi - lo < convergence:
            break
        mid = (lo + hi) / 2
        if predicate(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _set_objective(solver: Highs, col_indices: NDArray[np.int32], objective: Objective) -> None:
    """Set the full objective, its costs in a single C call and its offset.

    col_indices covers ALL variables (np.arange(n_vars)), so every column's
    cost is replaced — no stale costs from a previous objective can persist.
    """
    solver.changeColsCost(len(col_indices), col_indices, objective.costs)
    solver.changeObjectiveOffset(objective.offset)


@dataclass
class BlendWeightSearch:
    """Chooses blend weights for one optimization, putting the cost before the order.

    Attributes:
        too_small: Largest weight whose plan was cost-optimal but out of order.
        too_large: Smallest weight whose plan was not cost-optimal.

    """

    too_small: float = 0.0
    too_large: float = math.inf

    def next_weight(self, weight: float, *, cost_optimal: bool, order_optimal: bool) -> float | None:
        """Return the next weight to solve with, or None to keep the plan just solved.

        The weight moves half a decade away from a failing check until both bounds are
        known, then bisects between them.
        """
        if not cost_optimal:
            self.too_large = weight
            if self.too_small >= self.too_large:
                # A warm start can fail the cost at a weight that passed it before
                self.too_small = 0.0
            if self.too_small == 0.0:
                lowered = weight / _WEIGHT_STEP
                return lowered if lowered >= _MIN_BLEND_WEIGHT else None
            # Bisect toward the cost-optimal weight, or settle back on it when no gap is left
            if self.too_large > self.too_small * _WEIGHT_RESOLUTION:
                return math.sqrt(self.too_small * self.too_large)
            return self.too_small

        if order_optimal:
            return None

        self.too_small = weight
        if math.isinf(self.too_large):
            raised = weight * _WEIGHT_STEP
            return raised if raised <= _MAX_BLEND_WEIGHT else None
        if self.too_large > self.too_small * _WEIGHT_RESOLUTION:
            return math.sqrt(self.too_small * self.too_large)
        return None


def _bounds(solver: Highs, n_cols: int, entries: NDArray[np.intp]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return the lower and upper bounds of sorted columns and rows, with rows numbered after the columns.

    Each column and row is read from HiGHS by index, so the cost follows the number of entries asked for.
    """
    cols = entries[entries < n_cols].astype(np.int32)
    rows = (entries[entries >= n_cols] - n_cols).astype(np.int32)
    # HiGHS returns one placeholder value when asked for none, so each result is cut to the count it reports
    _, n_read_cols, _, col_lower, col_upper, _ = solver.getCols(len(cols), cols)
    _, n_read_rows, row_lower, row_upper, _ = solver.getRows(len(rows), rows)
    return (
        np.concatenate([col_lower[:n_read_cols], row_lower[:n_read_rows]]),
        np.concatenate([col_upper[:n_read_cols], row_upper[:n_read_rows]]),
    )


def _infeasible_for_cost(solver: Highs, all_col_indices: NDArray[np.int32], cost: Objective) -> bool:
    """Confirm an infeasible blended solve by solving for the cost alone.

    A badly scaled blend can be reported infeasible when the model is not, and a
    lower weight then finds the plan, so only a model infeasible for the cost too
    is treated as impossible.
    """
    _set_objective(solver, all_col_indices, cost)
    solver.run()
    return solver.getModelStatus() == HighsModelStatus.kInfeasible


def _status_without_presolve(solver: Highs) -> HighsModelStatus:
    """Solve again without presolve, which can only tell that a model is unbounded or infeasible, to learn which."""
    _, presolve = solver.getOptionValue("presolve")
    solver.setOptionValue("presolve", "off")
    try:
        solver.run()
    finally:
        solver.setOptionValue("presolve", presolve)
    return solver.getModelStatus()


def _ensure_optimal(solver: Highs) -> float:
    """Validate solver status and return the objective value."""
    status = solver.getModelStatus()
    if status != HighsModelStatus.kOptimal:
        raise SolverError(solver.modelStatusToString(status))
    return solver.getObjectiveValue()
