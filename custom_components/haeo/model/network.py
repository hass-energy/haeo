"""Network class for electrical system modeling and optimization."""

from dataclasses import dataclass, field
import logging
from typing import Any, overload

from highspy import Highs, HighsModelStatus
from highspy.highs import highs_cons, highs_linear_expression, highs_var
import numpy as np
from numpy.typing import NDArray

from .element import Element
from .elements import ELEMENTS, ModelElementConfig
from .elements.battery import Battery, BatteryElementConfig
from .elements.connection import Connection, ConnectionElementConfig, ConnectionOutputName
from .elements.node import Node, NodeElementConfig

_LOGGER = logging.getLogger(__name__)


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
    _solver: Highs = field(default_factory=Highs, repr=False)
    _primary_objective_constraint: highs_cons | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Set up the solver with logging callback."""
        self.periods = np.asarray(self.periods, dtype=float)
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
            # Get source and target elements
            source_element = self.elements.get(element_instance.source)
            target_element = self.elements.get(element_instance.target)

            if source_element is not None:
                source_element.register_connection(element_instance, "source")
            else:
                msg = (
                    f"Failed to register connection {name} with source {element_instance.source}: Not found or invalid"
                )
                raise ValueError(msg)

            if target_element is not None:
                target_element.register_connection(element_instance, "target")
            else:
                msg = (
                    f"Failed to register connection {name} with target {element_instance.target}: Not found or invalid"
                )
                raise ValueError(msg)
            element_instance.set_endpoints(source_element, target_element)

        return element_instance

    def cost(self) -> list[Any] | None:
        """Return aggregated objective expressions from all elements in the network.

        Discovers and calls all element cost() methods, combining their results into
        a list of objective expressions. Element costs are cached individually, so this
        aggregation is inexpensive.

        Returns:
            List of objective expressions or None if no objectives are defined

        """
        objectives = [
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

        Returns:
            The total optimization cost

        """
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

        # Get aggregated objectives from network (reactive - only rebuilds if any element cost invalidated)
        objectives = self.cost()

        h.clearLinearObjectives()

        if objectives is None:
            h.run()
            self._clear_primary_objective_constraint()
            return _ensure_optimal(h)

        primary = objectives[0] if objectives else None
        secondary: highs_linear_expression | highs_var | None
        if len(objectives) <= 1:
            secondary = None
        elif len(objectives) == 2:
            secondary = objectives[1]
        else:
            secondary = Highs.qsum(objectives[1:])

        if primary is None and secondary is not None:
            h.minimize(secondary)
            self._clear_primary_objective_constraint()
            _ensure_optimal(h)
            return 0.0

        if primary is None:
            h.run()
            self._clear_primary_objective_constraint()
            return _ensure_optimal(h)

        h.minimize(primary)
        primary_value = _ensure_optimal(h)
        if secondary is None:
            self._clear_primary_objective_constraint()
            return primary_value

        self._apply_primary_objective_constraint(primary, primary_value)
        h.minimize(secondary)
        _ensure_optimal(h)
        return primary_value

    def _apply_primary_objective_constraint(
        self,
        objective: highs_linear_expression | highs_var,
        optimal_value: float,
    ) -> None:
        """Constrain the primary objective for lexicographic optimization."""
        epsilon = _objective_epsilon(optimal_value)
        expression = _as_linear_expression(objective)
        constraint_expr = expression <= (optimal_value + epsilon)

        if self._primary_objective_constraint is None:
            self._primary_objective_constraint = self._solver.addConstr(constraint_expr)
            return

        self._update_constraint(self._primary_objective_constraint, constraint_expr)

    def _clear_primary_objective_constraint(self) -> None:
        """Disable the primary objective constraint if it exists."""
        if self._primary_objective_constraint is None:
            return

        cons = self._primary_objective_constraint
        expr = self._solver.getExpr(cons)
        self._solver.changeRowBounds(cons.index, float("-inf"), float("inf"))
        for var_idx in expr.idxs:
            self._solver.changeCoeff(cons.index, var_idx, 0.0)

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


def _combine_objective_lists(objectives: list[list[Any]]) -> list[Any]:
    """Combine objective expression lists by summing expressions at each index."""
    max_len = max((len(items) for items in objectives), default=0)
    combined: list[Any] = []
    for index in range(max_len):
        terms = [items[index] for items in objectives if len(items) > index]
        if not terms:
            continue
        if len(terms) == 1:
            combined.append(terms[0])
        else:
            combined.append(Highs.qsum(terms))
    return combined


def _objective_epsilon(value: float) -> float:
    """Return a small epsilon for lexicographic objective constraints."""
    return max(1e-6, abs(value) * 1e-9)


def _as_linear_expression(expression: highs_linear_expression | highs_var) -> highs_linear_expression:
    """Coerce a variable to a linear expression when needed."""
    if isinstance(expression, highs_linear_expression):
        return expression
    return Highs.qsum([expression])


def _ensure_optimal(solver: Highs) -> float:
    """Validate solver status and return the objective value."""
    status = solver.getModelStatus()
    if status != HighsModelStatus.kOptimal:
        msg = f"Optimization failed with status: {solver.modelStatusToString(status)}"
        raise ValueError(msg)
    return solver.getObjectiveValue()
