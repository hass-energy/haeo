"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression, highs_var

from .output_data import OutputData

if TYPE_CHECKING:
    from .connection import Connection

# Type alias for values that can be in constraint storage
type ConstraintValue = highs_cons | Sequence[highs_cons]

# Type alias for expression types (variables or expressions)
type ExpressionValue = highs_var | highs_linear_expression | float


class Element[OutputNameT: str, ConstraintNameT: str]:
    """Base class for electrical entities in energy system modeling.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (periods): hours (variable-width intervals)
    - Price: $/kWh
    """

    def __init__(self, name: str, periods: Sequence[float], *, solver: Highs) -> None:
        """Initialize an element.

        Args:
            name: Name of the entity
            periods: Sequence of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints

        """
        super().__init__()
        self.name = name
        self.periods = periods
        self._solver = solver

        # Constraint storage - dictionary allows re-entrancy
        self._constraints: dict[ConstraintNameT, ConstraintValue] = {}

        # Track connections for power balance
        self._connections: list[tuple[Connection, Literal["source", "target"]]] = []

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def register_connection(self, connection: "Connection", end: Literal["source", "target"]) -> None:
        """Register a connection to this element.

        Args:
            connection: The connection object
            end: Whether this element is the 'source' or 'target' of the connection

        """
        self._connections.append((connection, end))

    def connection_power(self, t: int) -> highs_linear_expression:
        """Return the net power from connections at time t.

        Positive means power flowing into this element from connections.
        Negative means power flowing out of this element to connections.

        Args:
            t: Time period index

        Returns:
            Sum of connection powers (HiGHS expression)

        """
        terms: list[highs_linear_expression] = []

        for conn, end in self._connections:
            if end == "source":
                # Power leaving source (negative)
                terms.append(-conn.power_source_target[t])
                # Power entering source from target (positive, with efficiency applied)
                terms.append(conn.power_target_source[t] * conn.efficiency_target_source[t])
            elif end == "target":
                # Power entering target from source (positive, with efficiency applied)
                terms.append(conn.power_source_target[t] * conn.efficiency_source_target[t])
                # Power leaving target (negative)
                terms.append(-conn.power_target_source[t])

        return Highs.qsum(terms) if terms else highs_linear_expression(0.0)

    def build_constraints(self) -> None:
        """Build network-dependent constraints (e.g., power balance).

        This method is called after all connections are registered and should
        create and store constraints in self._constraints dictionary.

        Elements should use connection_power(t) to get the net power from
        connections when building their power balance constraints.

        The solver is available via self._solver (set in __init__).

        Default implementation does nothing. Subclasses should override as needed.
        """

    def constraints(self) -> list[highs_cons]:
        """Return all constraints from this element.

        Returns:
            A flat list of all constraints stored in this element.

        """
        result: list[highs_cons] = []
        for value in self._constraints.values():
            if isinstance(value, Sequence):
                result.extend(value)
            else:
                result.append(value)
        return result

    def cost(self) -> Sequence[ExpressionValue]:
        """Return the cost expressions of the entity.

        Returns a sequence of cost expressions for aggregation at the network level.

        Units: $ = ($/kWh) * kW * period_hours

        Returns:
            Sequence of cost expressions (empty if no cost)

        Default implementation returns empty list. Subclasses should override as needed.

        """
        return []

    def outputs(self) -> Mapping[OutputNameT, OutputData]:
        """Return output specifications for the element.

        Each element should provide its own specific outputs.

        Default implementation returns empty dict. Subclasses should override as needed.
        """
        return {}
