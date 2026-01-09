"""Network class for electrical system modeling and optimization."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import logging
import time
from typing import Any

from highspy import Highs, HighsModelStatus
from highspy.highs import highs_cons, highs_linear_expression
from homeassistant.const import UnitOfTime

from .const import OutputType
from .element import Element
from .elements import ELEMENTS
from .elements.battery import Battery
from .elements.battery_balance_connection import BatteryBalanceConnection
from .elements.connection import Connection
from .output_data import OutputData
from .output_names import (
    NETWORK_OPTIMIZATION_COST,
    NETWORK_OPTIMIZATION_DURATION,
    NETWORK_OPTIMIZATION_STATUS,
    ModelOutputName,
)

_LOGGER = logging.getLogger(__name__)

# Optimization status value for initial state before optimization runs
OPTIMIZATION_STATUS_PENDING = "pending"

# Mapping from HighsModelStatus enum to snake_case status strings
# These are programming identifiers that get translated for display
_STATUS_MAP: dict[HighsModelStatus, str] = {
    HighsModelStatus.kNotset: "not_set",
    HighsModelStatus.kLoadError: "load_error",
    HighsModelStatus.kModelError: "model_error",
    HighsModelStatus.kPresolveError: "presolve_error",
    HighsModelStatus.kSolveError: "solve_error",
    HighsModelStatus.kPostsolveError: "postsolve_error",
    HighsModelStatus.kModelEmpty: "model_empty",
    HighsModelStatus.kOptimal: "optimal",
    HighsModelStatus.kInfeasible: "infeasible",
    HighsModelStatus.kUnboundedOrInfeasible: "unbounded_or_infeasible",
    HighsModelStatus.kUnbounded: "unbounded",
    HighsModelStatus.kObjectiveBound: "objective_bound",
    HighsModelStatus.kObjectiveTarget: "objective_target",
    HighsModelStatus.kTimeLimit: "time_limit",
    HighsModelStatus.kIterationLimit: "iteration_limit",
    HighsModelStatus.kUnknown: "unknown",
    HighsModelStatus.kSolutionLimit: "solution_limit",
}

# All possible optimization status values for enum options
OPTIMIZATION_STATUS_OPTIONS: tuple[str, ...] = tuple(sorted({OPTIMIZATION_STATUS_PENDING, *_STATUS_MAP.values()}))

# Cost output unit (virtual "optimization bucks" since costs are relative, not real currency)
COST_UNIT = "$"


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
    periods: Sequence[float]  # Period durations in hours (one per optimization interval)
    elements: dict[str, Element[Any]] = field(default_factory=dict)
    _solver: Highs = field(default_factory=Highs, repr=False)

    # Optimization result state (set after optimize() runs)
    _last_cost: float | None = field(default=None, repr=False)
    _last_status: str = field(default=OPTIMIZATION_STATUS_PENDING, repr=False)
    _last_duration: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        """Set up the solver with logging callback."""
        # Redirect HiGHS logging to Python logger at debug level
        self._solver.cbLogging += self._log_callback

        # Disable console output since we're capturing via callback
        output_off = False
        self._solver.setOptionValue("output_flag", output_off)
        self._solver.setOptionValue("log_to_console", output_off)

    @staticmethod
    def _log_callback(_log_type: int, message: str) -> None:
        """Log HiGHS messages to Python logger."""
        if message:
            _LOGGER.debug("HiGHS: %s", message.rstrip())

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def add(self, element_type: str, name: str, **kwargs: object) -> Element[Any]:
        """Add a new element to the network.

        Creates the element and registers connections. For parameter updates,
        modify the element's TrackedParam attributes directly - this will
        automatically invalidate dependent constraints for the next optimization.

        Args:
            element_type: Type of element as a string
            name: Name of the element
            **kwargs: Additional arguments specific to the element type

        Returns:
            The created element

        """
        # Create new element using registry
        # Cast to ModelElementType - validated by ELEMENTS dict lookup
        element_spec = ELEMENTS[element_type.lower()]  # type: ignore[index]
        element = element_spec.factory(name=name, periods=self.periods, solver=self._solver, **kwargs)
        self.elements[name] = element

        # Register connections immediately when adding Connection elements
        # (but not BatteryBalanceConnection - those register themselves via set_battery_references)
        if isinstance(element, Connection) and not isinstance(element, BatteryBalanceConnection):
            # Get source and target elements
            source_element = self.elements.get(element.source)
            target_element = self.elements.get(element.target)

            if source_element is not None:
                source_element.register_connection(element, "source")
            else:
                msg = f"Failed to register connection {name} with source {element.source}: Not found or invalid"
                raise ValueError(msg)

            if target_element is not None:
                target_element.register_connection(element, "target")
            else:
                msg = f"Failed to register connection {name} with target {element.target}: Not found or invalid"
                raise ValueError(msg)

        # Register battery balance connections with their battery sections
        if isinstance(element, BatteryBalanceConnection):
            # BatteryBalanceConnection uses source=upper, target=lower
            upper_element = self.elements.get(element.source)
            lower_element = self.elements.get(element.target)

            if not isinstance(upper_element, Battery):
                msg = f"Upper element '{element.source}' is not a battery"
                raise TypeError(msg)

            if not isinstance(lower_element, Battery):
                msg = f"Lower element '{element.target}' is not a battery"
                raise TypeError(msg)

            element.set_battery_references(upper_element, lower_element)

        return element

    def cost(self) -> highs_linear_expression | None:
        """Return aggregated cost expression from all elements in the network.

        Discovers and calls all element cost() methods, summing their results into
        a single expression. Element costs are cached individually, so this aggregation
        is inexpensive.

        Returns:
            Single aggregated cost expression or None if no costs

        """
        # Collect costs from all elements
        costs = [element_cost for element in self.elements.values() if (element_cost := element.cost()) is not None]

        # Aggregate into a single expression
        if not costs:
            return None
        if len(costs) == 1:
            return costs[0]
        return Highs.qsum(costs)

    def optimize(self) -> float:
        """Solve the optimization problem and return the cost.

        After optimization, access optimized values directly from elements and connections.
        Network-level outputs (cost, status, duration) are available via outputs().

        Collects constraints and costs from all elements. Calling element.constraints()
        automatically triggers constraint creation/updating via decorators. On first call,
        this builds all constraints. On subsequent calls, only invalidated constraints are
        rebuilt (those whose TrackedParam dependencies have changed).

        Returns:
            The total optimization cost

        Raises:
            ValueError: If optimization fails (status is set to failed before raising).

        """
        start_time = time.time()

        try:
            # Validate network before optimization
            self.validate()

            h = self._solver

            # Collect constraints from all elements (reactive - calling triggers decorator lifecycle)
            for element_name, element in self.elements.items():
                try:
                    element.constraints()
                except Exception as e:
                    msg = f"Failed to apply constraints for element '{element_name}'"
                    raise ValueError(msg) from e

            # Get aggregated cost from network (reactive - only rebuilds if any element cost invalidated)
            if (total_cost := self.cost()) is not None:
                h.minimize(total_cost)
            else:
                # No cost terms - just run to check feasibility
                h.run()

            # Check optimization status and store as snake_case string
            status = h.getModelStatus()
            self._last_status = _STATUS_MAP.get(status, "unknown")
            self._last_duration = time.time() - start_time

            if status == HighsModelStatus.kOptimal:
                cost = h.getObjectiveValue()
                self._last_cost = cost
                return cost

            msg = f"Optimization failed with status: {self._last_status}"
            raise ValueError(msg)

        except Exception:
            # Record failure duration before re-raising (status already set above if from HiGHS)
            self._last_duration = time.time() - start_time
            raise

    def validate(self) -> None:
        """Validate the network."""
        # Check that all connection elements have valid source and target elements
        for element in self.elements.values():
            if isinstance(element, Connection):
                if element.source not in self.elements:
                    msg = f"Source element '{element.source}' not found"
                    raise ValueError(msg)
                if element.target not in self.elements:
                    msg = f"Target element '{element.target}' not found"
                    raise ValueError(msg)
                if isinstance(self.elements[element.source], Connection):
                    msg = f"Source element '{element.source}' is a connection"
                    raise ValueError(msg)  # noqa: TRY004 value error is appropriate here
                if isinstance(self.elements[element.target], Connection):
                    msg = f"Target element '{element.target}' is a connection"
                    raise ValueError(msg)  # noqa: TRY004 value error is appropriate here

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

    def outputs(self) -> Mapping[ModelOutputName, OutputData]:
        """Return network-level outputs from the last optimization.

        Returns outputs for optimization cost, status, and duration.
        These are available after optimize() has been called.

        Returns:
            Dictionary mapping output names to OutputData instances.

        """
        return {
            NETWORK_OPTIMIZATION_COST: OutputData(
                type=OutputType.COST,
                unit=COST_UNIT,
                values=(self._last_cost,) if self._last_cost is not None else (0.0,),
            ),
            NETWORK_OPTIMIZATION_STATUS: OutputData(
                type=OutputType.STATUS,
                unit=None,
                values=(self._last_status,),
            ),
            NETWORK_OPTIMIZATION_DURATION: OutputData(
                type=OutputType.DURATION,
                unit=UnitOfTime.SECONDS,
                values=(self._last_duration,),
            ),
        }
