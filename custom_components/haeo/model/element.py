"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression, highs_var
import numpy as np
from numpy.typing import NDArray

from .output_data import OutputData

if TYPE_CHECKING:
    from .connection import Connection  # Circular import

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
        self.periods = np.asarray(periods)
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

    def connection_power(self) -> HighspyArray | NDArray[Any]:
        """Return the net power from connections for all time periods.

        Positive means power flowing into this element from connections.
        Negative means power flowing out of this element to connections.

        Returns:
            Array of connection powers for each time period (HiGHS array or numpy array of expressions)

        """
        if not self._connections:
            # No connections - create zero-valued variables for all periods
            # This ensures comparisons work properly with addConstrs
            return self._solver.addVariables(
                self.n_periods, lb=0, ub=0, name_prefix=f"{self.name}_no_conn_", out_array=True
            )

        # Accumulate power flows from all connections
        total_power: HighspyArray | NDArray[Any] = np.zeros(self.n_periods, dtype=object)

        for conn, end in self._connections:
            if end == "source":
                # Power leaving source (negative)
                total_power = total_power - conn.power_source_target
                # Power entering source from target (positive, with efficiency applied)
                total_power = total_power + conn.power_target_source * conn.efficiency_target_source
            elif end == "target":
                # Power entering target from source (positive, with efficiency applied)
                total_power = total_power + conn.power_source_target * conn.efficiency_source_target
                # Power leaving target (negative)
                total_power = total_power - conn.power_target_source

        return total_power

    def build_constraints(self) -> None:
        """Build network-dependent constraints (e.g., power balance).

        This method is called after all connections are registered and should
        create and store constraints in self._constraints dictionary.

        Elements should use connection_power() to get the net power from
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

    def extract_values(
        self, sequence: Sequence[Any] | HighspyArray | NDArray[Any] | highs_cons | None
    ) -> tuple[float, ...]:
        """Convert a sequence of HiGHS types to resolved values."""
        if sequence is None:
            return ()

        # Handle single highs_cons (not iterable)
        if isinstance(sequence, highs_cons):
            return (self._solver.constrDual(sequence),)

        # Convert to numpy array for batch processing
        arr = np.asarray(sequence, dtype=object)

        # Return empty tuple for empty arrays
        if len(arr) == 0:
            return ()

        # Check first item to determine type and use batch methods
        first_item = arr.flat[0]
        if isinstance(first_item, highs_cons):
            # Use batch constraint dual extraction
            return tuple(self._solver.constrDuals(arr).flat)

        # Default: use batch value extraction (handles highs_var and highs_linear_expression)
        return tuple(self._solver.vals(arr).flat)

    def outputs(self) -> Mapping[OutputNameT, OutputData]:
        """Return output specifications for the element.

        Each element should provide its own specific outputs.

        Default implementation returns empty dict. Subclasses should override as needed.
        """
        return {}
