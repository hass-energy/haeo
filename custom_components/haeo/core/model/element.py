"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from functools import reduce
import operator
from typing import Any, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .output_data import OutputData
from .reactive import OutputMethod, ReactiveConstraint, ReactiveCost, TrackedParam, constraint

ELEMENT_POWER_BALANCE: Final = "element_power_balance"


class Element[OutputNameT: str]:
    """Base class for electrical entities in energy system modeling.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (periods): hours (variable-width intervals)
    - Price: $/kWh

    Provides the generic lifecycle: naming, solver access, constraint/cost/output
    discovery via reactive decorators, and parameter access helpers.
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
    ) -> None:
        """Initialize an element.

        Args:
            name: Name of the entity
            periods: Array of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints
            output_names: Frozenset of valid output names for this element type (used for type narrowing)

        """
        self.name = name
        self.periods = np.asarray(periods, dtype=float)
        self._solver = solver
        self._output_names = output_names

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

    def extract_values(self, sequence: Sequence[Any] | HighspyArray | NDArray[Any] | None) -> tuple[float, ...]:
        """Convert a sequence of HiGHS types to resolved values."""
        if sequence is None:
            return ()

        # Convert to numpy array for batch processing
        arr = np.asarray(sequence, dtype=object)

        # Use batch value extraction (handles highs_var and highs_linear_expression)
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

    def cost(self) -> list[highs_linear_expression | None] | None:
        """Return aggregated objective expressions from this element.

        Discovers and calls all @cost decorated methods, combining their results into
        a list of objective expressions.

        Returns:
            List of objective expressions or None if no costs are defined

        """
        # Collect all cost expressions from @cost methods
        costs: list[list[highs_linear_expression]] = []
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if not isinstance(attr, ReactiveCost):
                continue

            # Call the cost method - this establishes dependency tracking
            method = getattr(self, name)
            if (cost_value := method()) is not None:
                if isinstance(cost_value, list):
                    costs.append([item for item in cost_value if item is not None])
                else:
                    costs.append([cost_value])

        if not costs:
            return None

        combined = _combine_objective_lists(costs)
        return combined or None


class NetworkElement[OutputNameT: str](Element[OutputNameT]):
    """Element that participates in network power balance.

    Extends Element with connection tracking, power production/consumption
    protocol, and per-tag power balance constraints. Node and Battery inherit
    from this class. Connection inherits directly from Element.
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        output_names: frozenset[OutputNameT],
        outbound_tags: set[int] | None = None,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a network element.

        Args:
            name: Name of the entity
            periods: Array of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints
            output_names: Frozenset of valid output names for this element type (used for type narrowing)
            outbound_tags: Tags that produced power can be placed on (None = all tags)
            inbound_tags: Tags that consumed power can draw from (None = all tags)

        """
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=output_names,
        )
        self.outbound_tags: set[int] | None = outbound_tags
        self.inbound_tags: set[int] | None = inbound_tags

        # Track connections for power balance
        self._connections: list[tuple[Any, Literal["source", "target"]]] = []

        # Lazily-created per-tag consumption decomposition variables
        self._consumed_by_tag: dict[int, HighspyArray] | None = None

        # Lazily-created per-tag production decomposition variables
        self._produced_by_tag: dict[int, HighspyArray] | None = None

    def register_connection(self, connection: Any, end: Literal["source", "target"]) -> None:
        """Register a connection to this element.

        Args:
            connection: The connection object
            end: Whether this element is the 'source' or 'target' of the connection

        """
        self._connections.append((connection, end))

    # --- Element power protocol ---

    def element_power_produced(self) -> HighspyArray | NDArray[Any] | None:
        """Return this element's power production expression.

        Positive values represent power injected into the network.
        Production is placed on ``outbound_tags``.
        Override in subclasses.  Default returns None (no production).
        """
        return None

    def element_power_consumed(self) -> HighspyArray | NDArray[Any] | None:
        """Return this element's power consumption expression.

        Positive values represent power absorbed from the network.
        Consumption draws from ``inbound_tags``.
        Override in subclasses.  Default returns None (no consumption).
        """
        return None

    # --- Connection power queries ---

    def connection_power(self) -> HighspyArray | NDArray[Any]:
        """Return the net power from connections for all time periods.

        Positive means power flowing into this element from connections.
        Negative means power flowing out of this element to connections.

        Returns:
            Array of connection powers for each time period (HiGHS array or numpy array of expressions)

        """
        if not self._connections:
            return np.zeros(self.n_periods)

        # Accumulate power flows from all connections
        total_power: HighspyArray | NDArray[Any] = np.zeros(self.n_periods, dtype=object)

        for conn, end in self._connections:
            if end == "source":
                total_power = total_power + conn.power_into_source
            else:
                total_power = total_power + conn.power_into_target

        return total_power

    def connection_power_for_tag(self, tag: int) -> HighspyArray | NDArray[Any]:
        """Return the net power from connections for a specific tag."""
        total_power: HighspyArray | NDArray[Any] = np.zeros(self.n_periods, dtype=object)
        for conn, end in self._connections:
            if tag not in conn.connection_tags():
                continue
            if end == "source":
                total_power = total_power + conn.power_into_source_for_tag(tag)
            else:
                total_power = total_power + conn.power_into_target_for_tag(tag)
        return total_power

    def connection_tags(self) -> set[int]:
        """Return the union of all tags from all connected connections."""
        tags: set[int] = set()
        for conn, _end in self._connections:
            tags.update(conn.connection_tags())
        return tags

    # --- Power balance ---

    def _get_consumed_by_tag(self, inbound: set[int]) -> dict[int, HighspyArray]:
        """Return per-tag consumption variables, creating them once on first call."""
        if self._consumed_by_tag is None:
            self._consumed_by_tag = {}
            for tag in sorted(inbound):
                self._consumed_by_tag[tag] = self._solver.addVariables(
                    self.n_periods,
                    lb=0,
                    name_prefix=f"{self.name}_ct{tag}_",
                    out_array=True,
                )
        return self._consumed_by_tag

    def _get_produced_by_tag(self, outbound: set[int]) -> dict[int, HighspyArray]:
        """Return per-tag production variables, creating them once on first call."""
        if self._produced_by_tag is None:
            self._produced_by_tag = {}
            for tag in sorted(outbound):
                self._produced_by_tag[tag] = self._solver.addVariables(
                    self.n_periods,
                    lb=0,
                    name_prefix=f"{self.name}_pt{tag}_",
                    out_array=True,
                )
        return self._produced_by_tag

    @constraint(output=True, unit="$/kW")
    def element_power_balance(self) -> list[highs_linear_expression] | None:
        """Per-tag power balance: for each tag, connection + produced - consumed == 0.

        Production is decomposed across ``outbound_tags`` via per-tag variables.
        Consumption is decomposed across ``inbound_tags`` via per-tag variables.
        Tags outside both sets are blocked (each connection's per-tag flow == 0).

        Output: shadow price indicating the marginal value of power at this element.
        Skipped when there are no connections and no external power.
        """
        tags = self.connection_tags()
        if not tags:
            produced = self.element_power_produced()
            consumed = self.element_power_consumed()
            if not self._connections and produced is None and consumed is None:
                return None
            balance = self.connection_power()
            if produced is not None:
                balance = balance + produced
            if consumed is not None:
                balance = balance - consumed
            return list(balance == 0)

        produced = self.element_power_produced()
        consumed = self.element_power_consumed()

        # Determine which tags can carry produced/consumed power
        outbound = set(tags) if self.outbound_tags is None else (self.outbound_tags & tags)
        inbound = set(tags) if self.inbound_tags is None else (self.inbound_tags & tags)

        constraints: list[highs_linear_expression] = []

        # Decompose production across outbound tags
        produced_by_tag: dict[int, HighspyArray] = {}
        if produced is not None:
            if outbound:
                produced_by_tag = self._get_produced_by_tag(outbound)
                constraints.extend(list(reduce(operator.add, produced_by_tag.values()) == produced))
            else:
                # Element produces but no outbound tags available — force production to 0
                constraints.extend(list(produced == 0))

        # Decompose consumption across inbound tags
        consumed_by_tag: dict[int, HighspyArray] = {}
        if consumed is not None:
            if inbound:
                consumed_by_tag = self._get_consumed_by_tag(inbound)
                constraints.extend(list(reduce(operator.add, consumed_by_tag.values()) == consumed))
            else:
                # Element consumes but no inbound tags available — force consumption to 0
                constraints.extend(list(consumed == 0))

        # Per-tag power balance
        for tag in sorted(tags):
            tag_prod = produced_by_tag.get(tag, 0)
            tag_cons = consumed_by_tag.get(tag, 0)
            if tag in outbound or tag in inbound:
                # Allowed tag: balance connection flow with production/consumption
                conn_tag = self.connection_power_for_tag(tag)
                constraints.extend(list(conn_tag + tag_prod - tag_cons == 0))
            else:
                # Blocked tag: force each connection's per-tag flow to 0 individually
                for conn, end in self._connections:
                    if tag not in conn.connection_tags():
                        continue
                    if end == "source":
                        constraints.extend(list(conn.power_into_source_for_tag(tag) == 0))
                    else:
                        constraints.extend(list(conn.power_into_target_for_tag(tag) == 0))

        return constraints if constraints else None


def _combine_objective_lists(
    objectives: list[list[highs_linear_expression]],
) -> list[highs_linear_expression | None]:
    """Combine objective expression lists by summing expressions at each index."""
    max_len = max((len(items) for items in objectives), default=0)
    combined: list[highs_linear_expression | None] = []
    for index in range(max_len):
        terms = [items[index] for items in objectives if len(items) > index]
        if not terms:
            combined.append(None)
        elif len(terms) == 1:
            combined.append(terms[0])
        else:
            combined.append(Highs.qsum(terms))
    return combined
