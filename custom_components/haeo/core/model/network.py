"""Network class for electrical system modeling and optimization."""

from collections.abc import Callable
from dataclasses import dataclass
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

from highspy import Highs, HighsModelStatus, HighsSolution
import numpy as np
from numpy.typing import NDArray

from .element import Element, NetworkElement
from .elements import ELEMENTS, ModelElementConfig
from .elements.battery import Battery, BatteryElementConfig
from .elements.connection import Connection, ConnectionElementConfig, ConnectionOutputName
from .elements.node import Node, NodeElementConfig
from .elements.policy_pricing import MeasuredFlows, PolicyPricing, PolicyPricingElementConfig
from .linear import INF, LinearArray, total
from .solver import Solver
from .util.solver_rows import AppliedRows, RowIndices, add_rows, change_bounds, update_rows

_LOGGER = logging.getLogger(__name__)


ObjectiveMode = Literal["lex", "blended", "calibrated"]
OnOffChoose = Literal["on", "off", "choose"]


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
# Factor the blend weight moves by until a weight is known on each side
_WEIGHT_STEP: Final = 10.0
# Narrowest gap between a weight too small for the order and one too large for
# the cost that is still searched
_WEIGHT_RESOLUTION: Final = 10.0**0.25
# Smallest blend weight tried when lowering it for the cost
_MIN_BLEND_WEIGHT: Final = 10.0**_CAL_LOG_LO
# Largest blend weight tried when raising it for the order
_MAX_BLEND_WEIGHT: Final = 10.0**_CAL_LOG_HI
# Slacks tried, smallest first, on the cost bound while the secondary is minimized,
# relative to the cost. Rounding in the cost just found can make a tighter bound
# infeasible, and a larger slack lets the secondary trade away more cost.
_LEX_COST_SLACKS: Final = (1e-9, 1e-6)
# HiGHS's default simplex iteration limit, restored after the optimality check
_UNLIMITED_ITERATIONS: Final = 2**31 - 1


@dataclass(frozen=True, kw_only=True)
class _SolverBase:
    """Shared HiGHS options applicable to all solver algorithms."""

    presolve: OnOffChoose = "choose"
    parallel: OnOffChoose = "choose"

    def _apply_common(self, h: Highs) -> None:
        h.setOptionValue("presolve", self.presolve)
        h.setOptionValue("parallel", self.parallel)


@dataclass(frozen=True, kw_only=True)
class SimplexTuning(_SolverBase):
    """HiGHS simplex solver options.

    simplex_strategy: 1=dual, 4=primal. Primal is ~25-30% faster on cold starts.
    simplex_scale_strategy: 0=off, 1=basic, 2=equilibration, 3=forced.
    feasibility_tolerance: primal and dual feasibility tolerance. Blended solves
    weight the secondary objective small enough to keep the cost exact, so the
    secondary's reduced costs must still register against this tolerance; at the
    HiGHS default of 1e-7 they can fall below it and leave ties unresolved.
    """

    simplex_strategy: int = 4
    simplex_scale_strategy: int = 0
    feasibility_tolerance: float = 1e-9

    def apply(self, h: Highs) -> None:
        """Apply simplex-specific options."""
        h.setOptionValue("solver", "simplex")
        self._apply_common(h)
        h.setOptionValue("simplex_strategy", self.simplex_strategy)
        h.setOptionValue("simplex_scale_strategy", self.simplex_scale_strategy)
        h.setOptionValue("primal_feasibility_tolerance", self.feasibility_tolerance)
        h.setOptionValue("dual_feasibility_tolerance", self.feasibility_tolerance)


@dataclass(frozen=True, kw_only=True)
class LexOptions(SimplexTuning):
    """Three-phase lexicographic optimization with clean shadow prices.

    Phase 1: minimize primary.
    Phase 2: minimize secondary with primary constrained.
    Phase 3: re-minimize primary with secondary constrained (epsilon slack).
    """

    mode: Literal["lex"] = "lex"


@dataclass(frozen=True, kw_only=True)
class BlendedOptions(SimplexTuning):
    """Weighted sum primary + weight * secondary, starting from ``blend_weight``.

    The weight is checked and moved like the calibrated mode's; only its starting
    value differs.
    """

    mode: Literal["blended"] = "blended"
    blend_weight: float = 1e-3


@dataclass(frozen=True, kw_only=True)
class CalibratedOptions(SimplexTuning):
    """Weighted sum primary + weight * secondary, starting from a calibrated weight.

    The first call binary-searches for the largest blend weight whose plan is
    cost-optimal and starts a little below it. A larger weight gives the
    secondary objective more influence, producing better tie-breaking in
    degenerate regions. Every call, the first included, then solves the blend
    and checks the plan, moving the weight if it fails.
    """

    mode: Literal["calibrated"] = "calibrated"


SolveOptions = LexOptions | BlendedOptions | CalibratedOptions


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
    ) -> None:
        """Create a network with the given period durations and solver options."""
        self.name = name
        self.periods = np.asarray(periods, dtype=float)
        self.elements: dict[str, Element[Any]] = {}
        self.options: SolveOptions = options or CalibratedOptions()
        self._solver = Solver()
        self._lex_row: tuple[RowIndices, AppliedRows] | None = None
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

        # Propagate to all elements (triggers TrackedParam invalidation)
        for element in self.elements.values():
            element.periods = self.periods

            # For Connection elements, also update their segments
            if isinstance(element, Connection):
                for segment in element.segments.values():
                    segment.periods = self.periods

    @overload
    def add(self, element_config: BatteryElementConfig) -> Battery: ...

    @overload
    def add(self, element_config: NodeElementConfig) -> Node: ...

    @overload
    def add(self, element_config: ConnectionElementConfig) -> Connection[ConnectionOutputName]: ...

    @overload
    def add(self, element_config: PolicyPricingElementConfig) -> PolicyPricing: ...

    def add(self, element_config: ModelElementConfig) -> Element[Any]:
        """Add a new element to the network.

        Creates the element and registers connections. For parameter updates,
        modify the element's TrackedParam attributes directly - this will
        automatically invalidate dependent constraints for the next optimization.

        For PolicyPricingElementConfig, resolves connection/tag references to
        LP power flow variables from already-added Connection elements.

        Args:
            element_config: Typed model element configuration dictionary

        Returns:
            The created element

        """
        name = element_config["name"]

        if element_config["element_type"] == "policy_pricing":
            return self._add_policy_pricing(element_config)

        element_type = element_config["element_type"]
        kwargs = {key: value for key, value in element_config.items() if key not in ("element_type", "name")}

        # Create new element using registry
        element_spec = ELEMENTS[element_type]
        element_instance: Element[Any] = element_spec.factory(
            name=name, periods=self.periods, solver=self._solver, **kwargs
        )
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

    def _add_policy_pricing(self, config: PolicyPricingElementConfig) -> PolicyPricing:
        """Create a PolicyPricing element by resolving connection/tag references."""
        name = config["name"]
        priced_flows: list[tuple[MeasuredFlows, int]] = []
        for term in config["terms"]:
            conn_name = term["connection"]
            tag = term["tag"]
            conn_element = self.elements.get(conn_name)
            if not isinstance(conn_element, Connection):
                msg = f"PolicyPricing '{name}' references unknown connection '{conn_name}'"
                raise TypeError(msg)
            if tag not in conn_element.measured_power:
                msg = f"PolicyPricing '{name}' references tag {tag} not on connection '{conn_name}'"
                raise ValueError(msg)
            priced_flows.append((conn_element, tag))

        element = PolicyPricing(
            name=name,
            periods=self.periods,
            solver=self._solver,
            price=config["price"],
            priced_flows=priced_flows,
            terms=config["terms"],
        )
        element.label = config.get("label", "")
        self.elements[name] = element
        return element

    def cost(self) -> tuple[LinearArray | None, LinearArray | None] | None:
        """Aggregate (primary, secondary) costs from all elements.

        Elements return either a single expression (primary only) or a
        (primary, secondary) tuple. Single expressions are promoted to
        the primary slot.
        """
        primaries: list[LinearArray] = []
        secondaries: list[LinearArray] = []

        for element in self.elements.values():
            element_cost = element.cost()
            if element_cost is None:
                continue
            if isinstance(element_cost, tuple):
                pri, sec = element_cost
                if pri is not None:
                    primaries.append(pri)
                if sec is not None:
                    secondaries.append(sec)
            else:
                primaries.append(element_cost)

        if not primaries and not secondaries:
            return None

        primary = total(primaries)
        secondary = total(secondaries)
        return (primary, secondary)

    def optimize(self) -> float:
        """Solve the optimization problem and return the primary objective value."""
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

        objectives = self.cost()
        if objectives is None:
            msg = "Network has no cost objectives — add connections with pricing segments"
            raise ValueError(msg)

        primary, secondary = objectives
        if primary is None:
            msg = "Network has no primary cost — add pricing to connections or nodes"
            raise ValueError(msg)
        if secondary is None:
            msg = "Network has no secondary cost — connections must generate time-preference objectives"
            raise ValueError(msg)

        n_vars = h.numVariables
        all_col_indices = np.arange(n_vars, dtype=np.int32)
        cost_vectors = _build_cost_vectors((primary, secondary), n_vars)

        if isinstance(self.options, LexOptions):
            return self._solve_lex(h, all_col_indices, cost_vectors, primary, secondary)

        if self._blend_weight is None:
            if isinstance(self.options, BlendedOptions):
                self._blend_weight = self.options.blend_weight
            else:
                self._blend_weight = self._calibrate_blend_weight(all_col_indices, cost_vectors)

        return self._solve_blended(h, all_col_indices, cost_vectors, self._blend_weight)

    def _solve_lex(
        self,
        h: Highs,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
        primary: LinearArray,
        secondary: LinearArray,
    ) -> float:
        """Lexicographic solve: Phase 1 primary, Phase 2 secondary, and Phase 3 to restore cost duals.

        Phase 3 re-minimizes the primary with the secondary constrained, so the plan
        and the cost duals come from the same basis.
        """
        h.clearLinearObjectives()

        # Phase 1: minimize primary
        _set_cost_vector(h, all_col_indices, cost_vectors[0])
        self._relax_lex_constraint()
        h.run()
        primary_value = _ensure_optimal(h)

        # Phase 2: minimize secondary with primary constrained, loosening the
        # constraint only if rounding makes it infeasible
        _set_cost_vector(h, all_col_indices, cost_vectors[1])
        slacks = iter(_LEX_COST_SLACKS)
        solved = False
        while not solved and (slack := next(slacks, None)) is not None:
            self._constrain_objective(primary, primary_value + slack * max(1.0, abs(primary_value)))
            h.run()
            solved = h.getModelStatus() == HighsModelStatus.kOptimal
        secondary_value = _ensure_optimal(h)

        # Phase 3: re-minimize primary with secondary constrained (restore duals)
        epsilon = max(1e-6, abs(secondary_value) * 1e-6)
        self._constrain_objective(secondary, secondary_value + epsilon)
        _set_cost_vector(h, all_col_indices, cost_vectors[0])
        h.run()
        _ensure_optimal(h)

        return primary_value

    def _solve_blended(
        self,
        h: Highs,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
        weight: float,
    ) -> float:
        """Solve primary + weight * secondary, moving the weight until the plan is cost-optimal and then in order.

        Each plan is checked at its own basis without moving it. The cost comes first:
        a plan that is not cost-optimal means the weight is too large for these
        inputs, and it is lowered. A cost-optimal plan with a move that leaves the
        cost unchanged and improves the secondary means the weight is too small for
        the secondary to register, and it is raised, though never to a weight this
        solve found too large for the cost.

        Which weights fail is only known for the current inputs, so only the weight
        settled on is kept between solves.

        The check leaves the cost objective's row duals at the plan's basis, so
        shadow prices are cost duals of the plan the solve chose.
        """
        h.clearLinearObjectives()
        self._relax_lex_constraint()
        search = BlendWeightSearch()
        next_weight: float | None = weight
        plan_cost = cost_optimal = 0.0
        while next_weight is not None:
            weight = next_weight
            plan_cost = _run_blended(h, all_col_indices, cost_vectors, weight)
            cost_optimal, order_optimal = _check_plan(h, all_col_indices, cost_vectors, weight)
            next_weight = search.next_weight(weight, cost_optimal=cost_optimal, order_optimal=order_optimal)
            if next_weight is not None:
                _LOGGER.debug("Blended plan at weight %.2e needs another solve; trying %.2e", weight, next_weight)

        if not cost_optimal:
            # The cost is the objective left set, so solving it gives the cheapest
            # plan and its duals, without the order
            _LOGGER.warning("No blend weight gives a cost-optimal plan; solving for the cost alone")
            h.run()
            plan_cost = _ensure_optimal(h)
        self._blend_weight = weight
        return plan_cost

    def _calibrate_blend_weight(
        self,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
    ) -> float:
        """Find the largest blend weight whose plan passes the cost check, and step just below it.

        A larger weight lets the secondary register over more of the problem, so the
        weight is placed just below that edge, ``_CAL_MARGIN`` log10 decades down,
        where later inputs are least likely to need another solve.

        This runs once, on the first optimization, so its extra solves are not paid
        again.
        """
        h = self._solver
        self._relax_lex_constraint()
        lo, hi = _CAL_LOG_LO, _CAL_LOG_HI

        def _cost_optimal(log_w: float) -> bool:
            _run_blended(h, all_col_indices, cost_vectors, 10.0**log_w)
            return _check_plan(h, all_col_indices, cost_vectors, 10.0**log_w)[0]

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

    def _constrain_objective(
        self,
        objective: LinearArray,
        optimal_value: float,
    ) -> None:
        """Set the single lex constraint to bound the given objective."""
        rows = objective <= optimal_value
        if self._lex_row is None:
            self._lex_row = add_rows(self._solver, rows)
        else:
            indices, applied = self._lex_row
            self._lex_row = (indices, update_rows(self._solver, indices, applied, rows))

    def _relax_lex_constraint(self) -> None:
        """Relax the lex constraint bounds so it is inactive."""
        if self._lex_row is not None:
            indices, applied = self._lex_row
            self._lex_row = (indices, change_bounds(self._solver, indices, applied, -INF, INF))

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


def _build_cost_vectors(
    objectives: tuple[LinearArray | None, LinearArray | None],
    n_vars: int,
) -> list[NDArray[np.float64]]:
    """Convert objective expressions to dense cost vectors.

    Pre-computing dense arrays enables single-call objective switching via
    ``changeColsCost`` instead of the expression-based ``setObjective``
    which zeros all columns then sets non-zero ones (two FFI round-trips
    per objective switch).
    """
    return [np.zeros(n_vars) if obj is None else obj.column_coefficients(n_vars) for obj in objectives]


def _set_cost_vector(
    solver: Highs,
    col_indices: NDArray[np.int32],
    costs: NDArray[np.float64],
) -> None:
    """Set the full objective cost vector in a single C call.

    col_indices covers ALL variables (np.arange(n_vars)), so every column's
    cost is replaced — no stale costs from a previous objective can persist.
    """
    solver.changeColsCost(len(col_indices), col_indices, costs)
    solver.changeObjectiveOffset(0.0)


def _run_blended(
    solver: Highs,
    col_indices: NDArray[np.int32],
    cost_vectors: list[NDArray[np.float64]],
    weight: float,
) -> float:
    """Solve primary + weight * secondary and return the plan's primary cost."""
    _set_cost_vector(solver, col_indices, cost_vectors[0] + weight * cost_vectors[1])
    solver.run()
    _ensure_optimal(solver)
    return float(cost_vectors[0] @ np.asarray(solver.allVariableValues()))


@dataclass
class BlendWeightSearch:
    """Chooses blend weights for one optimization, putting the cost before the order.

    The bounds found are only valid for this optimization's inputs and are not kept.

    Attributes:
        too_small: Largest weight whose plan was cost-optimal but out of order.
        too_large: Smallest weight whose plan was not cost-optimal.

    """

    too_small: float = 0.0
    too_large: float = math.inf

    def next_weight(self, weight: float, *, cost_optimal: bool, order_optimal: bool) -> float | None:
        """Return the next weight to solve with, or None to keep the plan just solved.

        A plan that is not cost-optimal lowers the weight, tenfold until a weight is
        known to be cost-optimal and then by bisection. A cost-optimal plan out of
        order raises the weight tenfold, or by bisection once a weight is known too
        large for the cost. A cost-optimal plan is kept when it is in
        order, or when no weight is left between the two known bounds.
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


def _price(solver: Highs, col_indices: NDArray[np.int32], costs: NDArray[np.float64]) -> None:
    """Price an objective at the current basis without moving the plan.

    The objective is solved with no simplex iterations allowed, so HiGHS only
    prices the current basis.
    """
    _set_cost_vector(solver, col_indices, costs)
    solver.setOptionValue("simplex_iteration_limit", 0)
    try:
        solver.run()
    finally:
        solver.setOptionValue("simplex_iteration_limit", _UNLIMITED_ITERATIONS)


def _reduced_costs(solution: HighsSolution) -> NDArray[np.float64]:
    """Return the reduced costs of the columns then the rows."""
    return np.concatenate(
        [np.asarray(solution.col_dual, dtype=np.float64), np.asarray(solution.row_dual, dtype=np.float64)]
    )


def _improving(
    reduced_costs: NDArray[np.float64],
    values: NDArray[np.float64],
    lower: NDArray[np.float64],
    upper: NDArray[np.float64],
) -> NDArray[np.bool_]:
    """Return which variables could move in a direction that lowers the objective.

    A variable can lower the objective by increasing when its reduced cost is
    negative and it is below its upper bound, or by decreasing when its reduced
    cost is positive and it is above its lower bound. Basic variables have zero
    reduced cost, so they are never flagged.
    """
    increases = (reduced_costs < -_REDUCED_COST_TOLERANCE) & (values < upper - _BOUND_TOLERANCE)
    decreases = (reduced_costs > _REDUCED_COST_TOLERANCE) & (values > lower + _BOUND_TOLERANCE)
    return increases | decreases


def _check_plan(
    solver: Highs,
    col_indices: NDArray[np.int32],
    cost_vectors: list[NDArray[np.float64]],
    weight: float,
) -> tuple[bool, bool]:
    """Return whether the blended plan just solved is cost-optimal, and whether it is in order.

    The plan is cost-optimal when pricing the cost at its basis leaves no move that
    lowers the cost. It is in order when, among moves that leave the cost unchanged,
    none lowers the secondary. Columns and rows are both variables here, a row's
    value being its activity.

    Reduced costs at a fixed basis are linear in the objective, so the secondary's
    are the blended solve's minus the cost's, divided by the weight, and the
    secondary needs no pricing of its own. The cost is priced last, so its row
    duals are the ones left for outputs.
    """
    blended = _reduced_costs(solver.getSolution())
    _price(solver, col_indices, cost_vectors[0])
    cost_optimal = solver.getInfo().max_dual_infeasibility <= _REDUCED_COST_TOLERANCE
    solution = solver.getSolution()
    cost = _reduced_costs(solution)
    secondary = (blended - cost) / weight

    # Only cost-free entries with a nonzero secondary reduced cost can lower it, so
    # the values and bounds are only read for those
    candidates = np.flatnonzero(
        (np.abs(cost) <= _REDUCED_COST_TOLERANCE) & (np.abs(secondary) > _REDUCED_COST_TOLERANCE)
    ).tolist()
    lp = solver.getLp()
    values = _gather(solution.col_value, solution.row_value, candidates)
    lower = _gather(lp.col_lower_, lp.row_lower_, candidates)
    upper = _gather(lp.col_upper_, lp.row_upper_, candidates)
    order_optimal = not _improving(secondary[candidates], values, lower, upper).any()
    return cost_optimal, order_optimal


def _gather(cols: list[float], rows: list[float], indices: list[int]) -> NDArray[np.float64]:
    """Return the entries at these indices of the columns' then the rows' values."""
    both = cols + rows
    return np.array([both[i] for i in indices], dtype=np.float64)


def _ensure_optimal(solver: Highs) -> float:
    """Validate solver status and return the objective value."""
    status = solver.getModelStatus()
    if status != HighsModelStatus.kOptimal:
        msg = f"Optimization failed with status: {solver.modelStatusToString(status)}"
        raise ValueError(msg)
    return solver.getObjectiveValue()
