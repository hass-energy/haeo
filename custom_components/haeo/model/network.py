"""Network class for electrical system modeling and optimization."""

from collections.abc import Callable, MutableSequence, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import io
import logging

from pulp import LpAffineExpression, LpConstraint, LpMinimize, LpProblem, LpStatus, LpVariable, getSolver, lpSum, value

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
        return element

    def constraints(self) -> Sequence[LpConstraint]:
        """Return constraints for the network."""
        constraints: MutableSequence[LpConstraint] = []

        # Add element-specific constraints (including connection elements)
        for element_name, element in self.elements.items():
            try:
                constraints.extend(element.constraints())
            except Exception as e:
                msg = f"Failed to generate constraints for element '{element_name}'"
                raise ValueError(msg) from e

        # Add power balance constraints for each element based on the connections
        # We need to identify connection elements and handle their power flows
        for element in self.elements.values():
            if not isinstance(element, Element):
                continue
            for t in range(self.n_periods):
                balance_terms: list[LpAffineExpression | LpVariable | float] = []

                # Add element's own consumption and production
                if element.power_consumption is not None:
                    balance_terms.append(-element.power_consumption[t])
                if element.power_production is not None:
                    balance_terms.append(element.power_production[t])

                # Add connection flows - check if this element is connected via connection elements
                for conn_element in self.elements.values():
                    if isinstance(conn_element, Connection):
                        if conn_element.source == element.name:
                            # Power leaving source (negative for balance)
                            balance_terms.append(-conn_element.power_source_target[t])
                            # Power entering source from target (positive, with efficiency applied)
                            balance_terms.append(
                                conn_element.power_target_source[t] * conn_element.efficiency_target_source[t]
                            )
                        elif conn_element.target == element.name:
                            # Power entering target from source (positive, with efficiency applied)
                            balance_terms.append(
                                conn_element.power_source_target[t] * conn_element.efficiency_source_target[t]
                            )
                            # Power leaving target (negative for balance)
                            balance_terms.append(-conn_element.power_target_source[t])

                # Power balance: sum of all terms should be zero
                if balance_terms:
                    constraints.append(lpSum(balance_terms) == 0)

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

        # Create the LP problem
        prob = LpProblem(f"{self.name}_optimization", LpMinimize)

        # Add the objective function (minimize total cost)
        prob += lpSum(c for element in self.elements.values() for c in element.cost())

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
