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

from highspy import Highs, HighsModelStatus, HighsVarType
import numpy as np
from numpy.typing import NDArray

from .element import Element, NetworkElement
from .elements import ELEMENTS, ModelElementConfig
from .elements.battery import Battery, BatteryElementConfig
from .elements.buffer import Buffer, BufferElementConfig
from .elements.connection import Connection, ConnectionElementConfig, ConnectionOutputName
from .elements.deferrable_load import DeferrableLoad, DeferrableLoadElementConfig
from .elements.node import Node, NodeElementConfig
from .elements.policy_pricing import MeasuredFlows, PolicyPricing, PolicyPricingElementConfig
from .elements.schedulable_load import SchedulableLoad, SchedulableLoadElementConfig
from .linear import LinearArray, total
from .solver import Solver
from .util.solver_rows import RowIndices

_LOGGER = logging.getLogger(__name__)


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
# Relative tolerance for a plan with integer columns to match the cost-only optimum
_INTEGER_COST_TOLERANCE: Final = 1e-7
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
    """

    presolve: OnOffChoose = "choose"
    parallel: OnOffChoose = "choose"
    simplex_strategy: int = 4
    simplex_scale_strategy: int = 0
    feasibility_tolerance: float = 1e-9

    def apply(self, h: Highs) -> None:
        """Apply the options to a solver."""
        h.setOptionValue("solver", "simplex")
        h.setOptionValue("presolve", self.presolve)
        h.setOptionValue("parallel", self.parallel)
        h.setOptionValue("simplex_strategy", self.simplex_strategy)
        h.setOptionValue("simplex_scale_strategy", self.simplex_scale_strategy)
        h.setOptionValue("primal_feasibility_tolerance", self.feasibility_tolerance)
        h.setOptionValue("dual_feasibility_tolerance", self.feasibility_tolerance)


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
        self.options = options or SolveOptions()
        self._solver = Solver()
        # Weight the last blended solve settled on, where the next one starts
        self._blend_weight: float | None = None
        # Columns elements require to be integer
        self._integer_cols: NDArray[np.int32] = np.zeros(0, dtype=np.int32)
        # Integer columns fixed at their solved values, with their own bounds
        self._fixed_integers: tuple[NDArray[np.float64], NDArray[np.float64]] | None = None
        # Cost-only optimum over the integer decisions, when there are integer columns
        self._integer_cost: float | None = None

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
    def add(self, element_config: DeferrableLoadElementConfig) -> DeferrableLoad: ...

    @overload
    def add(self, element_config: NodeElementConfig) -> Node: ...

    @overload
    def add(self, element_config: SchedulableLoadElementConfig) -> SchedulableLoad: ...

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

        if element_config["element_type"] == "buffer":
            return self._add_buffer(element_config)

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

    def _device_elements(self, buffer_name: str, device: str) -> list[NetworkElement[Any]]:
        """Return the network elements of a device a buffer names, raising when there are none.

        A device's elements are the one named after it and those named with
        its name as a prefix, such as an EV's ``EV:trip`` load.
        """
        elements = [
            element
            for name, element in self.elements.items()
            if (name == device or name.startswith(f"{device}:")) and isinstance(element, NetworkElement)
        ]
        if not elements:
            msg = f"Buffer '{buffer_name}' references unknown element '{device}'"
            raise TypeError(msg)
        return elements

    def _buffer_role(
        self, buffer_name: str, devices: list[str], *, source: bool, sink: bool
    ) -> list[NetworkElement[Any]]:
        """Return the elements of the named devices that only produce or only consume power.

        A device takes part through whichever of its elements fit the role, so
        an EV counts its trips as a load while its pack can hold the buffer.
        """
        return [
            element
            for device in devices
            for element in self._device_elements(buffer_name, device)
            if element.is_source == source and element.is_sink == sink
        ]

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

    def _add_buffer(self, config: BufferElementConfig) -> Buffer:
        """Create a Buffer element by resolving its loads, generation, and storage by name.

        The buffer reads what it needs from the elements and their connections,
        so any element can take part in a buffer.
        """
        name = config["name"]
        loads = self._buffer_role(name, config["loads"], source=False, sink=True)
        generation = self._buffer_role(name, config["generation"], source=True, sink=False)
        storage: list[Battery] = []
        for device in config["storage"]:
            batteries = [
                element
                for element_name, element in self.elements.items()
                if (element_name == device or element_name.startswith(f"{device}:")) and isinstance(element, Battery)
            ]
            if not batteries:
                msg = f"Buffer '{name}' references '{device}', which is not a battery"
                raise TypeError(msg)
            storage.extend(batteries)

        element = Buffer(
            name=name,
            periods=self.periods,
            solver=self._solver,
            kind=config["kind"],
            loads=loads,
            generation=generation,
            storage=storage,
            window=config["window"],
            level=config["level"],
            price=config["price"],
        )
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

        self._mark_integers()
        self._integer_cost = self._cost_optimum(all_col_indices, cost_vectors) if len(self._integer_cols) else None

        if self._blend_weight is None:
            self._blend_weight = self._calibrate_blend_weight(all_col_indices, cost_vectors)

        return self._solve_blended(all_col_indices, cost_vectors, self._blend_weight)

    def _solve_blended(
        self,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
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
            plan_cost, cost_optimal, order_optimal = self._solve_at(all_col_indices, cost_vectors, weight)
            next_weight = search.next_weight(weight, cost_optimal=cost_optimal, order_optimal=order_optimal)
            if next_weight is not None:
                _LOGGER.debug("Blended plan at weight %.2e needs another solve; trying %.2e", weight, next_weight)

        if not cost_optimal:
            # Keep the previous weight, and take the cheapest plan without the order
            _LOGGER.warning("No blend weight gives a cost-optimal plan; solving for the cost alone")
            _set_cost_vector(h, all_col_indices, cost_vectors[0])
            self._run_plan()
            return _ensure_optimal(h)

        if not order_optimal:
            _LOGGER.debug("No blend weight puts the plan in order; keeping the cost-optimal plan at %.2e", weight)
        self._blend_weight = weight
        return plan_cost

    def _solve_at(
        self,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
        weight: float,
    ) -> tuple[float, bool, bool]:
        """Solve primary + weight * secondary, and return the plan's cost, whether it is cost-optimal, and in order.

        The cost is priced at the plan's basis with no simplex iterations, which leaves
        the plan where it is and its cost duals for the shadow prices. Reduced costs at
        a fixed basis are linear in the objective, so the secondary's are the blended
        ones minus the cost's, over the weight. The plan is in order when no move that
        leaves the cost unchanged lowers the secondary. Rows count as variables too,
        with their activity as the value. A solve that fails counts as not
        cost-optimal, so the weight is lowered.

        Integer columns are fixed for the pricing, so reduced costs cannot see a
        cheaper integer decision. A plan with integer columns is cost-optimal only
        when its cost also matches the cost-only optimum. Among cost-optimal integer
        decisions, the mixed-integer solve of the blended objective already picks
        the one the secondary prefers.
        """
        h = self._solver
        _set_cost_vector(h, all_col_indices, cost_vectors[0] + weight * cost_vectors[1])
        self._run_plan()
        if h.getModelStatus() != HighsModelStatus.kOptimal:
            return math.nan, False, True
        plan_cost = float(cost_vectors[0] @ h.column_values())
        solution = h.getSolution()
        blended = np.concatenate([solution.col_dual, solution.row_dual])

        _set_cost_vector(h, all_col_indices, cost_vectors[0])
        h.setOptionValue("simplex_iteration_limit", 0)
        try:
            h.run()
        finally:
            h.setOptionValue("simplex_iteration_limit", _UNLIMITED_ITERATIONS)
        cost_optimal = h.getInfo().max_dual_infeasibility <= _REDUCED_COST_TOLERANCE
        if self._integer_cost is not None:
            # Reduced costs only see moves of the continuous columns, so a cheaper integer decision needs the optimum
            bound = self._integer_cost + _INTEGER_COST_TOLERANCE * max(1.0, abs(self._integer_cost))
            cost_optimal = cost_optimal and plan_cost <= bound

        solution = h.getSolution()
        cost = np.concatenate([solution.col_dual, solution.row_dual])
        secondary = (blended - cost) / weight

        # Only moves free in cost but not in the secondary can lower it, so only their values and bounds are read
        moves = np.flatnonzero(
            (np.abs(cost) <= _REDUCED_COST_TOLERANCE) & (np.abs(secondary) > _REDUCED_COST_TOLERANCE)
        )
        lp = h.getLp()
        value, lower, upper = (
            np.array([entries[i] for i in moves.tolist()], dtype=np.float64)
            for entries in (
                solution.col_value + solution.row_value,
                lp.col_lower_ + lp.row_lower_,
                lp.col_upper_ + lp.row_upper_,
            )
        )
        # A move lowers the secondary by raising a variable below its upper bound, or lowering one above its lower bound
        rises = (secondary[moves] < -_REDUCED_COST_TOLERANCE) & (value < upper - _BOUND_TOLERANCE)
        falls = (secondary[moves] > _REDUCED_COST_TOLERANCE) & (value > lower + _BOUND_TOLERANCE)
        return plan_cost, cost_optimal, not (rises | falls).any()

    def _mark_integers(self) -> None:
        """Collect the columns elements require to be integer, releasing any the previous solve fixed."""
        self._release_integers()
        integer = [variables for element in self.elements.values() if (variables := element.integer_variables())]
        self._integer_cols = np.unique(np.concatenate([variables.cols[:, 0] for variables in integer] or [[]])).astype(
            np.int32
        )
        if len(self._integer_cols):
            # Integer plans are compared against the cost-only optimum, so it must be exact
            self._solver.setOptionValue("mip_rel_gap", 0.0)

    def _release_integers(self) -> None:
        """Restore the bounds of integer columns fixed by the last plan solve and make them integer again."""
        h = self._solver
        cols = self._integer_cols
        if self._fixed_integers is not None:
            lower, upper = self._fixed_integers
            h.changeColsBounds(len(cols), cols, lower, upper)
            self._fixed_integers = None
        if len(cols):
            h.changeColsIntegrality(len(cols), cols, np.full(len(cols), HighsVarType.kInteger))

    def _cost_optimum(self, all_col_indices: NDArray[np.int32], cost_vectors: list[NDArray[np.float64]]) -> float:
        """Return the lowest cost over every plan, integer decisions included."""
        h = self._solver
        _set_cost_vector(h, all_col_indices, cost_vectors[0])
        self._run_plan()
        _ensure_optimal(h)
        return float(cost_vectors[0] @ h.column_values())

    def _run_plan(self) -> None:
        """Solve the current objective, leaving a linear program with valid duals.

        With integer columns the solve is mixed-integer, which reports no
        duals. The integer columns are then fixed at their solved values and
        made continuous, and the same objective is solved again as a linear
        program. The plan keeps its integer decisions and the duals the blend
        weight checks and shadow prices read become valid. The next plan solve
        releases the columns again.
        """
        h = self._solver
        self._release_integers()
        h.run()
        cols = self._integer_cols
        if len(cols) and h.getModelStatus() == HighsModelStatus.kOptimal:
            _, _, _, lower, upper, _ = h.getCols(len(cols), cols)
            values = np.round(h.column_values()[cols])
            h.changeColsIntegrality(len(cols), cols, np.full(len(cols), HighsVarType.kContinuous))
            h.changeColsBounds(len(cols), cols, values, values)
            self._fixed_integers = (np.asarray(lower), np.asarray(upper))
            h.run()

    def _calibrate_blend_weight(
        self,
        all_col_indices: NDArray[np.int32],
        cost_vectors: list[NDArray[np.float64]],
    ) -> float:
        """Return a weight ``_CAL_MARGIN`` decades below the largest whose plan is cost-optimal.

        The largest weight lets the secondary register most widely, and the margin
        leaves room for later inputs to move the edge before another solve is needed.
        """
        lo, hi = _CAL_LOG_LO, _CAL_LOG_HI

        def _cost_optimal(log_w: float) -> bool:
            return self._solve_at(all_col_indices, cost_vectors, 10.0**log_w)[1]

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


def _ensure_optimal(solver: Highs) -> float:
    """Validate solver status and return the objective value."""
    status = solver.getModelStatus()
    if status != HighsModelStatus.kOptimal:
        msg = f"Optimization failed with status: {solver.modelStatusToString(status)}"
        raise ValueError(msg)
    return solver.getObjectiveValue()
