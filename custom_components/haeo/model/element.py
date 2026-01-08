"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons
import numpy as np
from numpy.typing import NDArray

from .output_data import OutputData
from .reactive import CachedConstraint, CachedMethod, OutputMethod, TrackedParam

if TYPE_CHECKING:
    from .elements.connection import Connection


class Element[OutputNameT: str]:
    """Base class for electrical entities in energy system modeling.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (periods): hours (variable-width intervals)
    - Price: $/kWh

    This class integrates reactive parameter and constraint caching infrastructure.
    Elements can use TrackedParam for parameters and @constraint/@cost for methods.
    Dependency tracking is automatic.
    """

    def __init__(self, name: str, periods: Sequence[float], *, solver: Highs) -> None:
        """Initialize an element.

        Args:
            name: Name of the entity
            periods: Sequence of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints

        """
        self.name = name
        self.periods = np.asarray(periods)
        self._solver = solver

        # Track connections for power balance
        self._connections: list[tuple[Connection[Any], Literal["source", "target"]]] = []

    def __getitem__(self, key: str) -> Any:
        """Get a TrackedParam value by name.

        Args:
            key: Name of the TrackedParam

        Returns:
            The current value of the parameter

        Raises:
            KeyError: If no TrackedParam with this name exists

        """
        # Look up the descriptor on the class
        descriptor = getattr(type(self), key, None)
        if not isinstance(descriptor, TrackedParam):
            msg = f"{type(self).__name__!r} has no TrackedParam {key!r}"
            raise KeyError(msg)
        # Use normal attribute access to trigger the descriptor
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a TrackedParam value by name.

        Setting a value triggers invalidation of dependent constraints/costs.

        Args:
            key: Name of the TrackedParam
            value: New value to set

        Raises:
            KeyError: If no TrackedParam with this name exists

        """
        # Look up the descriptor on the class
        descriptor = getattr(type(self), key, None)
        if not isinstance(descriptor, TrackedParam):
            msg = f"{type(self).__name__!r} has no TrackedParam {key!r}"
            raise KeyError(msg)
        # Use normal attribute access to trigger the descriptor
        setattr(self, key, value)

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

        Discovers all @output decorated methods via reflection and calls them.
        The method name is used as the output name (dictionary key).
        """
        result: dict[OutputNameT, OutputData] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, OutputMethod):
                method = getattr(self, name)
                output_data = method()
                if output_data is not None:
                    result[name] = output_data  # type: ignore[literal-required]
            # Also include @constraint(output=True) decorated methods as shadow price outputs
            elif isinstance(attr, CachedConstraint) and attr.output:
                # Get the state for this constraint
                state_attr = f"_reactive_state_{name}"
                state = getattr(self, state_attr, None)
                if state is not None and "constraint" in state:
                    # Extract shadow prices from the constraint
                    cons = state["constraint"]
                    from .const import OutputType

                    output_data = OutputData(
                        type=OutputType.SHADOW_PRICE,
                        unit="$/kW",  # Default unit for shadow prices
                        values=self.extract_values(cons),
                    )
                    result[name] = output_data  # type: ignore[literal-required]
        return result

    def apply_constraints(self) -> None:
        """Apply constraints to the solver.

        Constraints are applied automatically by decorators when called.
        This method ensures all constraint methods are called to trigger their application.
        """
        # Find all constraint methods on this class
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, CachedMethod) and isinstance(attr, CachedConstraint):
                # Call the constraint method to trigger application
                method = getattr(self, name)
                method()
