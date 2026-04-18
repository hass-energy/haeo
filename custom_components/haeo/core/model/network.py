"""Network class for electrical system modeling and optimization."""

from dataclasses import dataclass, field
import logging
from typing import Any, Literal, overload

from highspy import Highs, HighsModelStatus, ObjSense
from highspy.highs import highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .element import Element, NetworkElement, _combine_objective_lists
from .elements import ELEMENTS, ModelElementConfig
from .elements.battery import Battery, BatteryElementConfig
from .elements.connection import Connection, ConnectionElementConfig, ConnectionOutputName
from .elements.node import Node, NodeElementConfig

_LOGGER = logging.getLogger(__name__)


ObjectiveMode = Literal["lex", "blended", "calibrated"]
SolverChoice = Literal["simplex", "ipm", "pdlp", "choose"]
OnOffChoose = Literal["on", "off", "choose"]


# Calibration search bounds in log10 space.  The secondary objective can
# be many orders of magnitude larger than the primary, so we need a wide
# range.  1e-12 is effectively zero influence; 1e-1 would dominate.
_CAL_LOG_LO = -12.0
_CAL_LOG_HI = -1.0
_CAL_MAX_STEPS = 40  # total bisection budget split across upper/lower searches
_CAL_CONVERGENCE = 0.01  # stop bisection when interval < this (log10 decades)


@dataclass(frozen=True)
class SolveOptions:
    """Options controlling Network optimization behavior.

    Combines our own multi-objective strategy with a curated set of HiGHS
    solver options that influence performance on this LP.

    See https://www.gams.com/latest/docs/S_HIGHS.html#HIGHS_OPTIONS for
    the underlying HiGHS option semantics.
    """

    # --- Multi-objective strategy ---
    # "lex" runs three solves for exact lexicographic optimization with
    # clean shadow prices (P1 primary, P2 secondary|P1, P3 primary|P2+e).
    # "blended" runs a single solve on (primary + blend_weight * secondary).
    # "calibrated" does a two-phase lex on the first call (P1, P2|P1),
    # then binary-searches for a blend weight that reproduces the lex
    # primary within tolerance. Subsequent calls use blended fast path.
    mode: ObjectiveMode = "calibrated"
    # Weight applied to the secondary objective in blended mode. Ignored
    # in calibrated mode (auto-determined). Should be small enough that
    # the secondary never overrides the primary at the scale of typical
    # problem coefficients.
    blend_weight: float = 1e-3
    # Relative tolerance on primary decision variable values for
    # calibrated mode's weight search. The calibration checks that
    # blended mode reproduces lex primary variable values within this
    # fraction of the largest variable magnitude.
    calibration_tolerance: float = 1e-4

    # --- HiGHS algorithm selection ---
    # "simplex" is best for warm-starts; "ipm" / "pdlp" do not warm-start.
    solver: SolverChoice = "simplex"
    # 1=dual, 4=primal. Primal simplex is ~25-30% faster on cold starts
    # (benchmarked across all scenarios) and equivalent on warm-starts.
    simplex_strategy: int = 4
    # "choose" lets HiGHS skip presolve on warm-starts; "on" forces it.
    presolve: OnOffChoose = "choose"
    # "choose" enables parallel only for large problems.
    parallel: OnOffChoose = "choose"
    # 0=off, 1=basic, 2=equilibration, 3=forced equilibration.
    # Scaling off gives a small additional cold-start improvement since
    # the LP coefficients are already well-conditioned (kW-based units).
    simplex_scale_strategy: int = 0
    # Crossover from interior point to a basic solution (ipm/pdlp only).
    run_crossover: OnOffChoose = "on"

    def apply(self, solver: Highs) -> None:
        """Apply HiGHS-tunable options to the given solver."""
        solver.setOptionValue("solver", self.solver)
        solver.setOptionValue("simplex_strategy", self.simplex_strategy)
        solver.setOptionValue("presolve", self.presolve)
        solver.setOptionValue("parallel", self.parallel)
        solver.setOptionValue("simplex_scale_strategy", self.simplex_scale_strategy)
        solver.setOptionValue("run_crossover", self.run_crossover)


# Calibration search bounds in log10 space.  The secondary objective can
# be many orders of magnitude larger than the primary, so we need a wide
# range.  1e-12 is effectively zero influence; 1e-1 would dominate.
_CAL_LOG_LO = -12.0
_CAL_LOG_HI = -1.0
_CAL_MAX_STEPS = 40  # total bisection budget split across upper/lower searches
_CAL_CONVERGENCE = 0.01  # stop bisection when interval < this (log10 decades)


@dataclass
class Network:
    """Network class for electrical system modeling.

    All values use kW-based units for numerical stability:
    - Power: kW
    - Energy: kWh
    - Time: hours (variable-width intervals)
    - Price: $/kWh

    Note: Periods should be provided in hours (conversion from seconds happens at the data loading boundary layer).
    """

    name: str
    periods: NDArray[np.floating[Any]]  # Period durations in hours (one per optimization interval)
    elements: dict[str, Element[Any]] = field(default_factory=dict)
    options: SolveOptions = field(default_factory=SolveOptions)
    _solver: Highs = field(default_factory=Highs, repr=False)
    _lex_constraint: highs_cons | None = field(default=None, init=False, repr=False)
    _calibrated_weight: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Set up the solver with logging callback and configured options."""
        self.periods = np.asarray(self.periods, dtype=float)
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

    def update_periods(self, new_periods: NDArray[np.floating[Any]]) -> None:
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

    def add(self, element_config: ModelElementConfig) -> Element[Any]:
        """Add a new element to the network.

        Creates the element and registers connections. For parameter updates,
        modify the element's TrackedParam attributes directly - this will
        automatically invalidate dependent constraints for the next optimization.

        Args:
            element_config: Typed model element configuration dictionary

        Returns:
            The created element

        """
        element_type = element_config["element_type"]
        name = element_config["name"]
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
                raise ValueError(msg)  # noqa: TRY004 value error is appropriate here

            if not isinstance(target_element, NetworkElement):
                msg = f"Target element '{element_instance.target}' is not a network participant"
                raise ValueError(msg)  # noqa: TRY004 value error is appropriate here

            source_element.register_connection(element_instance, "source")
            target_element.register_connection(element_instance, "target")
            element_instance.set_endpoints(source_element, target_element)

        return element_instance

    def cost(self) -> list[highs_linear_expression | None] | None:
        """Return aggregated objective expressions from all elements in the network.

        Discovers and calls all element cost() methods, combining their results into
        a list of objective expressions. Element costs are cached individually, so this
        aggregation is inexpensive.

        Returns:
            List of objective expressions or None if no objectives are defined

        """
        objectives: list[list[highs_linear_expression | None]] = [
            element_cost for element in self.elements.values() if (element_cost := element.cost()) is not None
        ]

        if not objectives:
            return None

        combined = _combine_objective_lists(objectives)
        return combined or None

    def optimize(self) -> float:
        """Solve the optimization problem and return the primary objective value.

        After optimization, access optimized values directly from elements and connections.

        Collects constraints and costs from all elements. Calling element.constraints()
        automatically triggers constraint creation/updating via decorators. On first call,
        this builds all constraints. On subsequent calls, only invalidated constraints are
        rebuilt (those whose TrackedParam dependencies have changed).

        Uses a lexicographic approach for multi-objective problems:
        1. Phase 1: minimize primary objective (lex constraint relaxed)
        2. Phase 2: minimize secondary objective (primary constrained to optimal)
        3. Phase 3 (lex mode only): re-minimize primary with secondary
           constrained (epsilon slack), restoring clean shadow prices

        In calibrated mode, Phase 3 is skipped because the solution is only
        used to calibrate a blend weight; subsequent calls use blended mode
        which produces proper duals from a single solve.

        Returns:
            The total optimization cost

        """
        h = self._solver

        # Collect constraints from all elements (reactive - calling triggers decorator lifecycle)
        for element_name, element in self.elements.items():
            try:
                element.constraints()
            except Exception as e:
                msg = f"Failed to apply constraints for element '{element_name}'"
                raise ValueError(msg) from e

        # Get aggregated objectives from network (reactive - only rebuilds if any element cost invalidated)
        objectives = self.cost()

        _clear_linear_objectives(h)

        if objectives is None:
            self._relax_lex_constraint()
            h.run()
            return _ensure_optimal(h)

        # Pre-compute cost vectors for each objective as dense arrays.
        # This avoids repeated Python→C FFI overhead from expression-based
        # setObjective() which zeros all columns then sets non-zero ones.
        n_vars = h.numVariables
        all_col_indices = np.arange(n_vars, dtype=np.int32)
        cost_vectors = _build_cost_vectors(objectives, n_vars)

        h.changeObjectiveSense(ObjSense.kMinimize)

        primary = objectives[0]
        secondary = objectives[1] if len(objectives) > 1 else None

        if primary is None:
            if secondary is not None:
                _set_cost_vector(h, all_col_indices, cost_vectors[1])
            self._relax_lex_constraint()
            h.run()
            _ensure_optimal(h)
            return 0.0

        # Calibrated mode with an existing weight uses blended fast path.
        use_blended = self.options.mode == "blended" or (
            self.options.mode == "calibrated" and self._calibrated_weight is not None
        )

        if use_blended and secondary is not None:
            if self.options.mode == "calibrated" and self._calibrated_weight is not None:
                return self._solve_blended(h, all_col_indices, cost_vectors, self._calibrated_weight)
            return self._solve_blended(h, all_col_indices, cost_vectors, self.options.blend_weight)

        # --- Lexicographic solve (also used for calibrated-mode first call) ---
        _set_cost_vector(h, all_col_indices, cost_vectors[0])

        # --- Phase 1: Minimize primary (lex constraint relaxed) ---
        self._relax_lex_constraint()
        h.run()
        primary_value = _ensure_optimal(h)

        if secondary is not None:
            # --- Phase 2: Minimize secondary (constrain primary) ---
            self._constrain_objective(primary, primary_value)
            _set_cost_vector(h, all_col_indices, cost_vectors[1])
            h.run()
            secondary_value = _ensure_optimal(h)

            if self.options.mode == "lex":
                # --- Phase 3: Re-minimize primary (swap constraint to secondary) ---
                # Restores shadow prices that reflect pure primary sensitivities.
                # Skipped in calibrated mode where only variable values are needed.
                epsilon = max(1e-6, abs(secondary_value) * 1e-6)
                self._constrain_objective(secondary, secondary_value + epsilon)
                _set_cost_vector(h, all_col_indices, cost_vectors[0])
                h.run()
                _ensure_optimal(h)

        # After lex solve, calibrate the blend weight for future calls.
        if self.options.mode == "calibrated" and secondary is not None:
            lex_values = np.asarray(h.allVariableValues())
            self._calibrated_weight = self._calibrate_blend_weight(
                all_col_indices,
                cost_vectors,
                lex_values,
                self.options.calibration_tolerance,
            )

        return primary_value

    def _solve_blended(
        self,
        h: Highs,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
        weight: float,
    ) -> float:
        """Single-solve weighted sum: primary + weight * secondary."""
        self._relax_lex_constraint()
        blended = cost_vectors[0] + weight * cost_vectors[1]
        _set_cost_vector(h, all_col_indices, blended)
        h.run()
        _ensure_optimal(h)
        return float(cost_vectors[0] @ np.asarray(h.allVariableValues()))

    def _calibrate_blend_weight(
        self,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
        lex_values: NDArray[np.float64],
        tolerance: float,
    ) -> float:
        """Find the center of the safe weight zone for blended mode.

        Performs two binary searches in log10 space to locate the upper
        and lower boundaries where blended mode reproduces the lex
        primary decision variable values.  Returns the geometric mean
        (midpoint in log space) to maximize robustness against problem
        perturbations.

        The blended objective for variable *i* is
        ``c1_i + w * c2_i``.  Since the perturbation scales linearly
        with *w*, equal multiplicative changes in *w* produce equal
        effects on the solution — so log space is the natural coordinate
        for both searching and centering.

        The "safe zone" is the weight range where the LP solver lands on
        the same vertex as lex for all primary variables.  Centering
        within this zone provides maximum margin against coefficient
        changes shifting the boundary.
        """
        h = self._solver

        # Primary variable indices: nonzero coefficient in primary cost vector.
        pri_mask = cost_vectors[0] != 0
        lex_pri = lex_values[pri_mask]

        # If no variables have primary cost, any weight is safe.
        if lex_pri.size == 0:
            return self.options.blend_weight

        # Absolute tolerance scaled to variable magnitudes.
        abs_tol = max(1e-8, float(np.max(np.abs(lex_pri))) * tolerance)

        def _primary_vars_match(log_w: float) -> bool:
            w = 10.0**log_w
            self._relax_lex_constraint()
            blended = cost_vectors[0] + w * cost_vectors[1]
            _set_cost_vector(h, all_col_indices, blended)
            h.run()
            if h.getModelStatus() != HighsModelStatus.kOptimal:
                return False
            bl_vals = np.asarray(h.allVariableValues())
            max_diff = float(np.max(np.abs(bl_vals[pri_mask] - lex_pri)))
            return max_diff <= abs_tol

        lo, hi = _CAL_LOG_LO, _CAL_LOG_HI
        half_budget = _CAL_MAX_STEPS // 2

        # --- Find upper edge: highest weight where primary vars match ---
        if _primary_vars_match(hi):
            upper = hi
        elif not _primary_vars_match(lo):
            _LOGGER.warning(
                "Calibration: primary vars don't match even at w=1e%g",
                lo,
            )
            # Restore lex solution and fall back.
            _set_cost_vector(h, all_col_indices, cost_vectors[0])
            self._relax_lex_constraint()
            h.run()
            _ensure_optimal(h)
            return 10.0**lo
        else:
            # lo is good, hi is bad — bisect to find upper boundary.
            u_lo, u_hi = lo, hi
            for _ in range(half_budget):
                if u_hi - u_lo < _CAL_CONVERGENCE:
                    break
                mid = (u_lo + u_hi) / 2
                if _primary_vars_match(mid):
                    u_lo = mid
                else:
                    u_hi = mid
            upper = u_lo

        # --- Find lower edge: lowest weight where primary vars match ---
        if upper == lo or _primary_vars_match(lo):
            lower = lo
        else:
            # upper is good, lo is bad — bisect to find lower boundary.
            l_lo, l_hi = lo, upper
            for _ in range(half_budget):
                if l_hi - l_lo < _CAL_CONVERGENCE:
                    break
                mid = (l_lo + l_hi) / 2
                if _primary_vars_match(mid):
                    l_hi = mid
                else:
                    l_lo = mid
            lower = l_hi

        center = (upper + lower) / 2
        weight = 10.0**center

        _LOGGER.debug(
            "Calibrated blend weight: %.2e (log10=%.2f, safe zone [%.1f, %.1f])",
            weight,
            center,
            lower,
            upper,
        )

        # Final solve at center weight to warm-start future blended calls.
        self._relax_lex_constraint()
        blended = cost_vectors[0] + weight * cost_vectors[1]
        _set_cost_vector(h, all_col_indices, blended)
        h.run()
        _ensure_optimal(h)

        return weight

    def _constrain_objective(
        self,
        objective: highs_linear_expression,
        optimal_value: float,
    ) -> None:
        """Set the single lex constraint to bound the given objective."""
        constraint_expr = objective <= optimal_value

        if self._lex_constraint is None:
            self._lex_constraint = self._solver.addConstr(constraint_expr)
        else:
            self._update_constraint(self._lex_constraint, constraint_expr)

    def _relax_lex_constraint(self) -> None:
        """Relax the lex constraint bounds so it is inactive."""
        if self._lex_constraint is not None:
            self._solver.changeRowBounds(self._lex_constraint.index, float("-inf"), float("inf"))

    def _update_constraint(
        self,
        cons: highs_cons,
        expr: highs_linear_expression,
    ) -> None:
        """Update an existing constraint with a new expression."""
        old_expr = self._solver.getExpr(cons)
        old_bounds = old_expr.bounds
        new_bounds = expr.bounds

        if old_bounds != new_bounds:
            if new_bounds is not None:
                self._solver.changeRowBounds(cons.index, new_bounds[0], new_bounds[1])
            elif old_bounds is not None:
                self._solver.changeRowBounds(cons.index, float("-inf"), float("inf"))

        old_coeffs = dict(zip(old_expr.idxs, old_expr.vals, strict=True))
        new_coeffs = dict(zip(expr.idxs, expr.vals, strict=True))
        all_vars = set(old_coeffs) | set(new_coeffs)

        for var_idx in all_vars:
            old_val = old_coeffs.get(var_idx, 0.0)
            new_val = new_coeffs.get(var_idx, 0.0)
            if old_val != new_val:
                self._solver.changeCoeff(cons.index, var_idx, new_val)

    def constraints(self) -> dict[str, dict[str, highs_cons | list[highs_cons]]]:
        """Return all constraints from all elements in the network.

        Returns:
            Dictionary mapping element names to their constraint dictionaries.
            Each constraint dictionary maps constraint method names to constraint objects.

        """
        result: dict[str, dict[str, highs_cons | list[highs_cons]]] = {}
        for element_name, element in self.elements.items():
            if element_constraints := element.constraints():
                result[element_name] = element_constraints
        return result


def _clear_linear_objectives(solver: Highs) -> None:
    """Clear any multiobjective state."""
    solver.clearLinearObjectives()


def _build_cost_vectors(
    objectives: list[highs_linear_expression | None],
    n_vars: int,
) -> list[NDArray[np.float64]]:
    """Convert objective expressions to dense cost vectors.

    Pre-computing dense arrays enables single-call objective switching via
    ``changeColsCost`` instead of the expression-based ``setObjective``
    which zeros all columns then sets non-zero ones (two FFI round-trips
    per objective switch).
    """
    vectors: list[NDArray[np.float64]] = []
    for obj in objectives:
        vec = np.zeros(n_vars, dtype=np.float64)
        if obj is not None:
            idxs, vals = obj.unique_elements()
            vec[idxs] = vals
        vectors.append(vec)
    return vectors


def _set_cost_vector(
    solver: Highs,
    col_indices: NDArray[np.int32],
    costs: NDArray[np.float64],
) -> None:
    """Set the full objective cost vector in a single C call."""
    solver.changeColsCost(len(col_indices), col_indices, costs)
    solver.changeObjectiveOffset(0.0)


def _ensure_optimal(solver: Highs) -> float:
    """Validate solver status and return the objective value."""
    status = solver.getModelStatus()
    if status != HighsModelStatus.kOptimal:
        msg = f"Optimization failed with status: {solver.modelStatusToString(status)}"
        raise ValueError(msg)
    return solver.getObjectiveValue()
