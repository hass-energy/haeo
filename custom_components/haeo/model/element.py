"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons
import numpy as np
from numpy.typing import NDArray

from .output_data import OutputData
from .reactive import ReactiveElement

if TYPE_CHECKING:
    from .connection import Connection


class Element[OutputNameT: str](ReactiveElement):
    """Base class for electrical entities in energy system modeling.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (periods): hours (variable-width intervals)
    - Price: $/kWh

    Elements define constraints using @cached_constraint decorators and
    costs using @cached_cost decorators. Parameters that can change between
    optimizations should use TrackedParam descriptors.
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

        # Track connections for power balance
        self._connections: list[tuple[Connection[Any], Literal["source", "target"]]] = []

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def register_connection(self, connection: "Connection[Any]", end: Literal["source", "target"]) -> None:
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
                # Power flowing into this element (as source)
                total_power = total_power + conn.power_into_source
            elif end == "target":
                # Power flowing into this element (as target)
                total_power = total_power + conn.power_into_target

        return total_power

    def extract_values(
        self, sequence: Sequence[Any] | HighspyArray | NDArray[Any] | highs_cons | None
    ) -> tuple[float, ...]:
        """Convert a sequence of HiGHS types to resolved values."""
        if sequence is None:
            return ()

        # Convert to numpy array for batch processing
        arr = np.asarray(sequence, dtype=object)

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
