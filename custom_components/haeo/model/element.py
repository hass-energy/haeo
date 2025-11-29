"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, MutableSequence, Sequence
from typing import TYPE_CHECKING, Literal

from pulp import LpAffineExpression, LpConstraint, lpSum

from .output_data import OutputData

if TYPE_CHECKING:
    from .connection import Connection


class Element[OutputNameT: str, ConstraintNameT: str]:
    """Base class for electrical entities in energy system modeling.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (periods): hours (variable-width intervals)
    - Price: $/kWh
    """

    def __init__(self, name: str, periods: Sequence[float]) -> None:
        """Initialize an element.

        Args:
            name: Name of the entity
            periods: Sequence of time period durations in hours (one per optimization interval)

        """
        self.name = name
        self.periods = periods

        # Constraint storage - dictionary allows re-entrancy
        self._constraints: dict[ConstraintNameT, LpConstraint | Sequence[LpConstraint]] = {}

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

    def connection_power(self, t: int) -> LpAffineExpression:
        """Return the net power from connections at timestep t.

        Positive means power flowing into this element from connections.
        Negative means power flowing out of this element to connections.

        Args:
            t: Time period index

        Returns:
            Sum of connection powers (LP expression)

        """
        terms: list[LpAffineExpression] = []

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

        return lpSum(terms) if terms else LpAffineExpression(constant=0.0)

    def build_constraints(self) -> None:
        """Build network-dependent constraints (e.g., power balance).

        This method is called after all connections are registered and should
        create and store constraints in self._constraints dictionary.

        Elements should use connection_power(t) to get the net power from
        connections when building their power balance constraints.

        Default implementation does nothing. Subclasses should override as needed.
        """

    def constraints(self) -> Sequence[LpConstraint]:
        """Return all constraints for this element.

        Returns:
            Flattened sequence of all stored constraints

        """
        result: MutableSequence[LpConstraint] = []
        for constraint_or_sequence in self._constraints.values():
            if isinstance(constraint_or_sequence, Sequence):
                result.extend(constraint_or_sequence)
            else:
                result.append(constraint_or_sequence)
        return result

    def cost(self) -> Sequence[LpAffineExpression]:
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
