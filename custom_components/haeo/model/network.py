"""Network class for electrical system modeling and optimization."""

from collections.abc import MutableSequence, Sequence
from dataclasses import dataclass, field

from pulp import LpConstraint, LpMinimize, LpProblem, LpStatus, lpSum, value

from .battery import Battery
from .connection import Connection
from .constant_load import ConstantLoad
from .element import Element
from .forecast_load import ForecastLoad
from .generator import Generator
from .grid import Grid
from .net import Net


@dataclass
class Network:
    """Network class for electrical system modeling."""

    name: str
    period: int
    n_periods: int
    elements: dict[str, Element] = field(default_factory=dict)
    sensor_data_available: bool = True

    def add(self, element_type: str, name: str, **kwargs: object) -> Element:
        """Add an element to the network by type.

        Args:
            element_type: Type of element as a string
            name: Name of the element
            **kwargs: Additional arguments specific to the element type

        Returns:
            The created element

        """
        # Set n_periods if not provided and required by element type
        self.elements[name] = {
            "battery": Battery,
            "generator": Generator,
            "constant_load": ConstantLoad,
            "forecast_load": ForecastLoad,
            "grid": Grid,
            "net": Net,
            "connection": Connection,
        }[element_type.lower()](name=name, period=self.period, n_periods=self.n_periods, **kwargs)
        return self.elements[name]

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
            for t in range(self.n_periods):
                balance_terms = []

                # Add element's own consumption and production
                if isinstance(element, Element):
                    if element.power_consumption is not None:
                        balance_terms.append(-element.power_consumption[t])
                    if element.power_production is not None:
                        balance_terms.append(element.power_production[t])

                # Add connection flows - check if this element is connected via connection elements
                for conn_element in self.elements.values():
                    if isinstance(conn_element, Connection):
                        if conn_element.source == element.name:
                            # Power leaving the element (negative for balance)
                            balance_terms.append(-conn_element.power[t])
                        elif conn_element.target == element.name:
                            # Power entering the element (positive for balance)
                            balance_terms.append(conn_element.power[t])

                # Power balance: sum of all terms should be zero
                if balance_terms:
                    constraints.append(lpSum(balance_terms) == 0)

        return constraints

    def cost(self) -> float:
        """Return the cost expression for the network."""
        return lpSum([e.cost() for e in self.elements.values() if e.cost() != 0])

    def optimize(self) -> float:
        """Solve the optimization problem and return the cost.

        After optimization, access optimized values directly from elements and connections.

        Returns:
            The total optimization cost

        """
        # Validate network before optimization
        self.validate()

        # Create the LP problem
        prob = LpProblem(f"{self.name}_optimization", LpMinimize)

        # Add the objective function (minimize cost)
        prob += self.cost(), "Total_Cost"

        # Add all constraints
        for constraint in self.constraints():
            prob += constraint

        # Solve the problem
        status = prob.solve()

        if status == 1:  # Optimal solution found
            objective_value = value(prob.objective) if prob.objective is not None else 0.0
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
