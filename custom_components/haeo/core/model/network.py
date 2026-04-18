"""Network class for electrical system modeling and optimization."""

from dataclasses import dataclass, field
import logging
from typing import Any, Literal, overload

from highspy import Highs, HighsModelStatus
from highspy.highs import highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .element import Element, NetworkElement
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


@dataclass(frozen=True, kw_only=True)
class _SolverTuning:
    """HiGHS solver options shared across all objective modes.

    See https://www.gams.com/latest/docs/S_HIGHS.html#HIGHS_OPTIONS for
    the underlying HiGHS option semantics.
    """

    solver: SolverChoice = "simplex"
    simplex_strategy: int = 4
    presolve: OnOffChoose = "choose"
    parallel: OnOffChoose = "choose"
    simplex_scale_strategy: int = 0
    run_crossover: OnOffChoose = "on"

    def apply(self, h: Highs) -> None:
        """Apply HiGHS-tunable options to the given solver."""
        h.setOptionValue("solver", self.solver)
        h.setOptionValue("simplex_strategy", self.simplex_strategy)
        h.setOptionValue("presolve", self.presolve)
        h.setOptionValue("parallel", self.parallel)
        h.setOptionValue("simplex_scale_strategy", self.simplex_scale_strategy)
        h.setOptionValue("run_crossover", self.run_crossover)


@dataclass(frozen=True, kw_only=True)
class LexOptions(_SolverTuning):
    """Three-phase lexicographic optimization with clean shadow prices.

    Phase 1: minimize primary.
    Phase 2: minimize secondary with primary constrained.
    Phase 3: re-minimize primary with secondary constrained (epsilon slack).
    """

    mode: Literal["lex"] = "lex"


@dataclass(frozen=True, kw_only=True)
class BlendedOptions(_SolverTuning):
    """Single-solve weighted sum: primary + blend_weight * secondary."""

    mode: Literal["blended"] = "blended"
    blend_weight: float = 1e-3


@dataclass(frozen=True, kw_only=True)
class CalibratedOptions(_SolverTuning):
    """Two-phase lex on first call, then calibrated blended fast path.

    The first call runs phases 1 and 2 of lex, then binary-searches for
    a blend weight that reproduces the lex primary variable values within
    tolerance. Subsequent calls use the blended fast path.
    """

    mode: Literal["calibrated"] = "calibrated"
    calibration_tolerance: float = 1e-4


SolveOptions = LexOptions | BlendedOptions | CalibratedOptions


# Calibration search bounds in log10 space.  The secondary objective can
# be many orders of magnitude larger than the primary, so we need a wide
# range.  1e-12 is effectively zero influence; 1e-1 would dominate.


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
    options: SolveOptions = field(default_factory=CalibratedOptions)
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

    def cost(self) -> tuple[Any, Any] | None:
        """Aggregate (primary, secondary) costs from all elements.

        Elements return either a single expression (primary only) or a
        (primary, secondary) tuple. Single expressions are promoted to
        the primary slot.
        """
        primaries: list[Any] = []
        secondaries: list[Any] = []

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

        primary = Highs.qsum(primaries) if primaries else None
        secondary = Highs.qsum(secondaries) if secondaries else None
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
            msg = "Network has no primary cost — add pricing segments to connections"
            raise ValueError(msg)
        if secondary is None:
            msg = "Network has no secondary cost — connections must generate time-preference objectives"
            raise ValueError(msg)

        n_vars = h.numVariables
        all_col_indices = np.arange(n_vars, dtype=np.int32)
        cost_vectors = _build_cost_vectors((primary, secondary), n_vars)

        if isinstance(self.options, BlendedOptions):
            return self._solve_blended(h, all_col_indices, cost_vectors, self.options.blend_weight)

        if isinstance(self.options, CalibratedOptions) and self._calibrated_weight is not None:
            return self._solve_blended(h, all_col_indices, cost_vectors, self._calibrated_weight)

        return self._solve_lex(h, all_col_indices, cost_vectors, primary, secondary)

    def _solve_lex(
        self,
        h: Highs,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
        primary: Any,
        secondary: Any,
    ) -> float:
        """Lexicographic solve: Phase 1 primary, Phase 2 secondary, Phase 3 restore."""
        _clear_linear_objectives(h)

        # Phase 1: minimize primary
        _set_cost_vector(h, all_col_indices, cost_vectors[0])
        self._relax_lex_constraint()
        h.run()
        primary_value = _ensure_optimal(h)

        # Phase 2: minimize secondary with primary constrained
        self._constrain_objective(primary, primary_value)
        _set_cost_vector(h, all_col_indices, cost_vectors[1])
        h.run()
        secondary_value = _ensure_optimal(h)

        if isinstance(self.options, LexOptions):
            # Phase 3: re-minimize primary with secondary constrained (restore duals)
            epsilon = max(1e-6, abs(secondary_value) * 1e-6)
            self._constrain_objective(secondary, secondary_value + epsilon)
            _set_cost_vector(h, all_col_indices, cost_vectors[0])
            h.run()
            _ensure_optimal(h)

        # Calibrate blend weight for future calls
        if isinstance(self.options, CalibratedOptions):
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
        _clear_linear_objectives(h)
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
            return 1e-3  # safe default — no primary cost to distort

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
    objectives: tuple[Any, Any],
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
