"""Network class for electrical system modeling and optimization."""

from collections.abc import Callable, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import io
import logging
from typing import Any

from pulp import LpConstraint, LpMinimize, LpProblem, LpStatus, getSolver, lpSum, value

from .battery import Battery
from .connection import Connection
from .element import Element
from .source_sink import SourceSink

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
    periods: Sequence[float]  # Period durations in hours (one per optimization interval)
    elements: dict[str, Element[Any, Any]] = field(default_factory=dict)

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def add(self, element_type: str, name: str, **kwargs: object) -> Element[Any, Any]:
        """Add an element to the network by type.

        Args:
            element_type: Type of element as a string
            name: Name of the element
            **kwargs: Additional arguments specific to the element type

        Returns:
            The created element

        """
        factories: dict[str, Callable[..., Element[Any, Any]]] = {
            "battery": Battery,
            "connection": Connection,
            "source_sink": SourceSink,
        }

        factory = factories[element_type.lower()]
        element = factory(name=name, periods=self.periods, **kwargs)
        self.elements[name] = element

        # Register connections immediately when adding Connection elements
        if isinstance(element, Connection):
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
        prob = LpProblem(f"{self.name}_optimization", LpMinimize)

        # Add the objective function (minimize total cost)
        prob += lpSum(c for element in self.elements.values() for c in element.cost())

        # Add element constraints
        for element in self.elements.values():
            for constraint in element.constraints():
                prob += constraint

        # Get the specified solver
        try:
            solver = getSolver(optimizer, msg=0)
        except Exception as e:
            msg = f"Failed to get solver '{optimizer}': {e}"
            raise ValueError(msg) from e

        # Capture stdout and stderr during optimization
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Solve the problem
                status = prob.solve(solver)
        finally:
            # Always log the captured output for debugging
            if stdout_capture.getvalue().strip():
                _LOGGER.debug("Optimization stdout: %s", stdout_capture.getvalue())
            if stderr_capture.getvalue().strip():
                _LOGGER.debug("Optimization stderr: %s", stderr_capture.getvalue())

        if status == 1:  # Optimal solution found
            return value(prob.objective) if prob.objective is not None else 0.0

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
