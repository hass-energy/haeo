"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from typing import Any, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .output_data import OutputData
from .reactive import OutputMethod, ReactiveConstraint, ReactiveCost, TrackedParam, constraint, cost

ELEMENT_POWER_BALANCE: Final = "element_power_balance"


class Element[OutputNameT: str]:
    """Base class for electrical entities in energy system modeling.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (periods): hours (variable-width intervals)
    - Price: $/kWh

    Subclasses implement ``element_power_produced()`` and
    ``element_power_consumed()`` to declare their external power.  The base
    class uses these to build per-tag power balance constraints with
    source_tag/access_list enforcement when tagged connections exist.
    """

    # TrackedParam for periods - enables reactive invalidation when periods change
    periods: TrackedParam[NDArray[np.floating[Any]]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        output_names: frozenset[OutputNameT],
        source_tag: int | None = None,
        access_list: list[int] | None = None,
    ) -> None:
        """Initialize an element.

        Args:
            name: Name of the entity
            periods: Array of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints
            output_names: Frozenset of valid output names for this element type (used for type narrowing)
            source_tag: If set, only this tag can carry outbound power from this element.
            access_list: If set, only these tags can be consumed at this element.

        """
        self.name = name
        self.periods = np.asarray(periods, dtype=float)
        self._solver = solver
        self._output_names = output_names
        self._source_tag = source_tag
        self._access_list: set[int] | None = set(access_list) if access_list else None

        # Track connections for power balance
        self._connections: list[tuple[Any, Literal["source", "target"]]] = []

    def __getitem__(self, key: str | int) -> Any:
        """Get a value by name or index.

        Args:
            key: Name of the TrackedParam

        Returns:
            The current value of the parameter

        Raises:
            KeyError: If no TrackedParam with this name exists

        """
        segments = getattr(self, "segments", None)
        if isinstance(key, int):
            if isinstance(segments, Mapping):
                try:
                    return list(segments.values())[key]
                except IndexError as exc:
                    msg = f"{type(self).__name__!r} has no segment at index {key}"
                    raise KeyError(msg) from exc
            msg = f"{type(self).__name__!r} does not support indexed access"
            raise KeyError(msg)

        if isinstance(segments, Mapping) and key in segments:
            return segments[key]

        # Look up the descriptor on the class
        descriptor = getattr(type(self), key, None)
        if isinstance(descriptor, TrackedParam):
            return getattr(self, key)
        if hasattr(self, key):
            return getattr(self, key)
        msg = f"{type(self).__name__!r} has no attribute {key!r}"
        raise KeyError(msg)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a value by name.

        Setting a value triggers invalidation of dependent constraints/costs.

        Args:
            key: Name of the TrackedParam
            value: New value to set

        Raises:
            KeyError: If no TrackedParam with this name exists

        """
        # Look up the descriptor on the class
        descriptor = getattr(type(self), key, None)
        if isinstance(descriptor, TrackedParam):
            setattr(self, key, value)
            return
        if hasattr(self, key):
            setattr(self, key, value)
            return
        msg = f"{type(self).__name__!r} has no attribute {key!r}"
        raise KeyError(msg)

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    @property
    def source_tag(self) -> int | None:
        """Return the source tag for this element, or None."""
        return self._source_tag

    @source_tag.setter
    def source_tag(self, value: int | None) -> None:
        """Set the source tag."""
        self._source_tag = value

    @property
    def access_list(self) -> set[int] | None:
        """Return the set of tags this element can consume, or None for all."""
        return self._access_list

    @access_list.setter
    def access_list(self, value: set[int] | list[int] | None) -> None:
        """Set the access list."""
        self._access_list = set(value) if value else None

    def register_connection(self, connection: Any, end: Literal["source", "target"]) -> None:
        """Register a connection to this element.

        Args:
            connection: The connection object
            end: Whether this element is the 'source' or 'target' of the connection

        """
        self._connections.append((connection, end))

    # --- Element power protocol ---

    def element_power_produced(self) -> HighspyArray | NDArray[Any] | int:
        """Return this element's power production expression.

        Positive values represent power injected into the network.
        Production is tagged with this element's ``source_tag``.
        Override in subclasses.  Default returns 0.
        """
        return 0

    def element_power_consumed(self) -> HighspyArray | NDArray[Any] | int:
        """Return this element's power consumption expression.

        Positive values represent power absorbed from the network.
        Consumption is distributed across allowed tags (per ``access_list``).
        Override in subclasses.  Default returns 0.
        """
        return 0

    # --- Connection power queries ---

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
                total_power = total_power + conn.power_into_source
            elif end == "target":
                total_power = total_power + conn.power_into_target

        return total_power

    def connection_power_for_tag(self, tag: int) -> HighspyArray | NDArray[Any]:
        """Return the net power from connections for a specific tag."""
        if not self._connections:
            return self._solver.addVariables(
                self.n_periods, lb=0, ub=0, name_prefix=f"{self.name}_no_conn_t{tag}_", out_array=True
            )

        total_power: HighspyArray | NDArray[Any] = np.zeros(self.n_periods, dtype=object)
        for conn, end in self._connections:
            if tag not in conn.connection_tags():
                continue
            if end == "source":
                total_power = total_power + conn.power_into_source_for_tag(tag)
            elif end == "target":
                total_power = total_power + conn.power_into_target_for_tag(tag)
        return total_power

    def connection_tags(self) -> set[int]:
        """Return the union of all tags from all connected connections."""
        tags: set[int] = set()
        for conn, _end in self._connections:
            tags.update(conn.connection_tags())
        return tags

    # --- Per-tag element power decomposition ---

    @constraint(output=True, unit="$/kW")
    def element_power_balance(self) -> list[highs_linear_expression] | None:
        """Total power balance: connection_power + produced - consumed == 0.

        Output: shadow price indicating the marginal value of power at this element.
        Skipped when there are no connections and no external power.
        """
        produced = self.element_power_produced()
        consumed = self.element_power_consumed()

        is_zero_prod = isinstance(produced, (int, float)) and produced == 0
        is_zero_cons = isinstance(consumed, (int, float)) and consumed == 0

        if not self._connections and is_zero_prod and is_zero_cons:
            return None

        return list(self.connection_power() + produced - consumed == 0)

    @constraint
    def element_tag_balance(self) -> list[highs_linear_expression] | None:
        """Per-tag power balance using produced/consumed decomposition.

        For each tag:
        - source_tag: ``conn_tag + produced - consumed_from_tag == 0``
        - allowed tag: ``conn_tag - consumed_from_tag == 0``
        - other tag: ``conn_tag == 0``

        Sum constraint: ``sum(consumed_from_tag) == consumed``
        """
        tags = self.connection_tags()
        if not tags:
            return None

        produced = self.element_power_produced()
        consumed = self.element_power_consumed()

        # Determine which tags can carry consumed power
        allowed_tags = set(tags)
        if self._access_list is not None:
            allowed_tags &= self._access_list

        # Create per-tag consumption variables (skip if no consumption)
        has_consumption = not (isinstance(consumed, (int, float)) and consumed == 0)
        consumed_by_tag: dict[int, HighspyArray] = {}
        if has_consumption:
            for tag in sorted(allowed_tags):
                consumed_by_tag[tag] = self._solver.addVariables(
                    self.n_periods, lb=0, name_prefix=f"{self.name}_ct{tag}_", out_array=True,
                )
            if consumed_by_tag:
                self._solver.addConstrs(
                    sum(consumed_by_tag.values()) == consumed  # type: ignore[arg-type]
                )

        # Per-tag power balance
        constraints: list[highs_linear_expression] = []
        for tag in sorted(tags):
            conn_tag = self.connection_power_for_tag(tag)

            # Production appears only on source_tag
            tag_prod = produced if (self._source_tag is not None and tag == self._source_tag) else 0

            # Consumption from this tag (if allowed)
            tag_cons = consumed_by_tag.get(tag, 0)

            constraints.extend(list(conn_tag + tag_prod - tag_cons == 0))

        return constraints if constraints else None

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

        Discovers all @output and @constraint(output=True) decorated methods via
        reflection and calls their get_output() method to retrieve OutputData.
        The method name is used as the output name (dictionary key).
        """
        result: dict[OutputNameT, OutputData] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            # Resolve output name for OutputMethod (supports custom names).
            if isinstance(attr, OutputMethod):
                output_name = attr.output_name
            elif isinstance(attr, ReactiveConstraint):
                output_name = name
            else:
                continue

            if output_name in self._output_names and (output_data := attr.get_output(self)) is not None:
                result[output_name] = output_data  # type: ignore[assignment]  # name validated by `in` check at runtime
        return result

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Return all constraints from this element.

        Discovers and calls all @constraint decorated methods. Calling the methods
        triggers automatic constraint creation/updating in the solver via decorators.

        Returns:
            Dictionary mapping constraint method names to constraint objects

        """
        result: dict[str, highs_cons | list[highs_cons]] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, ReactiveConstraint):
                # Call the constraint method to trigger decorator lifecycle
                method = getattr(self, name)
                method()

                # Get the state after calling to collect constraints
                state_attr = f"_reactive_state_{name}"
                state = getattr(self, state_attr, None)
                if state is not None and "constraint" in state:
                    cons = state["constraint"]
                    result[name] = cons
        return result

    @cost
    def cost(self) -> Any:
        """Return aggregated cost expression from this element.

        Discovers and calls all @cost decorated methods, summing their results into
        a single expression. The result is cached by the @cost decorator, which
        automatically tracks dependencies on all underlying @cost methods.

        Returns:
            Single aggregated cost expression (highs_linear_expression) or None if no costs

        """
        # Get this method's name from the decorator to avoid hardcoding
        this_method_name = type(self).cost._name  # type: ignore[attr-defined]  # noqa: SLF001 (intentional access to decorator's name)

        # Collect all cost expressions from @cost methods (excluding this one)
        costs: list[Any] = []
        for name in dir(type(self)):
            # Skip self to avoid infinite recursion
            if name == this_method_name:
                continue
            attr = getattr(type(self), name, None)
            if not isinstance(attr, ReactiveCost):
                continue

            # Call the cost method - this establishes dependency tracking
            method = getattr(self, name)
            if (cost_value := method()) is not None:
                if isinstance(cost_value, list):
                    costs.extend(cost_value)
                else:
                    costs.append(cost_value)

        # Aggregate costs into a single expression
        if not costs:
            return None
        if len(costs) == 1:
            return costs[0]
        # Sum all cost expressions
        return sum(costs[1:], costs[0])
