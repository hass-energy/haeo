"""Network class for electrical system modeling and optimization."""

from collections.abc import Callable, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import io
import logging
from typing import cast

from pulp import LpConstraint, LpMinimize, LpProblem, LpStatus, getSolver, lpSum, value

from .battery import Battery
from .connection import Connection
from .element import Element
from .grid import Grid
from .load import Load
from .node import Node
from .photovoltaics import Photovoltaics

_LOGGER = logging.getLogger(__name__)


@dataclass
class Network:
    """Network class for electrical system modeling.

    All values use kW-based units for numerical stability:
    - Power: kW
    - Energy: kWh
    - Time: hours
    - Price: $/kWh

    Note: Period should be provided in hours (conversion from seconds happens at the data loading boundary layer).
    """

    name: str
    period: float  # Period in hours
    n_periods: int
    elements: dict[str, Element | Connection] = field(default_factory=dict)

    def add(self, element_type: str, name: str, **kwargs: object) -> Element | Connection:
        """Add an element to the network by type.

        Args:
            element_type: Type of element as a string
            name: Name of the element
            **kwargs: Additional arguments specific to the element type

        Returns:
            The created element

        """
        factories: dict[str, Callable[..., Element | Connection]] = {
            "battery": Battery,
            "photovoltaics": Photovoltaics,
            "load": Load,
            "grid": Grid,
            "node": Node,
            "connection": Connection,
        }

        factory = factories[element_type.lower()]
        element = factory(name=name, period=self.period, n_periods=self.n_periods, **kwargs)
        self.elements[name] = element

        # Register connections immediately when adding Connection elements
        if isinstance(element, Connection):
            # Get source and target elements
            source_element = self.elements.get(element.source)
            target_element = self.elements.get(element.target)

            if source_element is not None and isinstance(source_element, Element):
                source_element.register_connection(element, "source")
            if target_element is not None and isinstance(target_element, Element):
                target_element.register_connection(element, "target")

        return element

    def constraints(self) -> Sequence[LpConstraint]:
        """Return constraints for the network.

        This aggregates all constraints stored in the elements after build_constraints()
        has been called during the optimization phase.
        """
        constraints: list[LpConstraint] = []

        # Add all constraints from elements
        for element_name, element in self.elements.items():
            try:
                constraints.extend(element.constraints())
            except Exception as e:
                msg = f"Failed to get constraints for element '{element_name}'"
                raise ValueError(msg) from e

        return constraints

    def cost(self) -> float:
        """Return the cost expression for the network."""
        result = lpSum([e.cost() for e in self.elements.values() if e.cost() != 0])
        # lpSum returns either a LpAffineExpression or a number (0 if empty list)
        # The LpAffineExpression is duck-typed as float in PuLP's optimization context
        return cast("float", result)

    def optimize(self, optimizer: str = "HiGHS") -> float:
        """Solve the optimization problem and return the cost.

        After optimization, access optimized values directly from elements and connections.

        Args:
            optimizer: The solver to use for optimization (defaults to HiGHS)

        Returns:
            The total optimization cost

        """
        # Validate network before optimization
        self.validate()

        # Compilation phase: build constraints for all elements
        for element_name, element in self.elements.items():
            try:
                element.build_constraints()
            except Exception as e:
                msg = f"Failed to build constraints for element '{element_name}'"
                raise ValueError(msg) from e

        # Create the LP problem
        prob = LpProblem(f"{self.name}_optimization", LpMinimize)  # type: ignore[no-untyped-call]

        # Add the objective function (minimize cost)
        prob += self.cost(), "Total_Cost"

        # Add all constraints
        for constraint in self.constraints():
            prob += constraint

        # Get the specified solver
        try:
            solver = getSolver(optimizer)
        except Exception as e:
            msg = f"Failed to get solver '{optimizer}': {e}"
            raise ValueError(msg) from e

        # Capture stdout and stderr during optimization
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Solve the problem
                status = prob.solve(solver)  # type: ignore[no-untyped-call]
        finally:
            # Always log the captured output for debugging
            if stdout_capture.getvalue().strip():
                _LOGGER.debug("Optimization stdout: %s", stdout_capture.getvalue())
            if stderr_capture.getvalue().strip():
                _LOGGER.debug("Optimization stderr: %s", stderr_capture.getvalue())

        if status == 1:  # Optimal solution found
            objective_value = value(prob.objective) if prob.objective is not None else 0.0  # type: ignore[no-untyped-call]
            # Handle PuLP return types - value() can return various types
            return float(objective_value) if isinstance(objective_value, (int, float)) else 0.0

        msg = f"Optimization failed with status: {LpStatus[status]}"
        raise ValueError(msg)

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
