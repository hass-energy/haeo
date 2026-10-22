"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping
from typing import Final, Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from .component import ModelComponent
from .const import OutputType
from .linear import LinearArray, Rows
from .output_data import OutputData
from .reactive import TrackedParam, applied_constraint, constraint, output
from .solver import Solver
from .util.solver_rows import RowIndices

ELEMENT_POWER_BALANCE: Final = "element_power_balance"


class _ConnectionLike(Protocol):
    """Structural type for connection objects registered with a NetworkElement.

    Describes only the members NetworkElement needs from a connection. Kept as a
    Protocol (rather than importing Connection) to avoid a circular import between
    element.py and elements/connection.py, which imports Element.
    """

    @property
    def power_into_source(self) -> LinearArray: ...

    @property
    def power_into_target(self) -> LinearArray: ...

    def connection_tags(self) -> set[int]: ...

    def power_into_source_for_tag(self, tag: int) -> LinearArray: ...

    def power_into_target_for_tag(self, tag: int) -> LinearArray: ...


class Element[OutputNameT: str](ModelComponent):
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
    periods: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
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

    def __getitem__(self, key: str | int) -> object:
        """Get a value by name.

        Args:
            key: Name of the TrackedParam or attribute

        Returns:
            The current value of the parameter

        Raises:
            KeyError: If the element has no value with this name, or the key is an index
            AttributeError: If the TrackedParam has not been set

        """
        if isinstance(key, int):
            msg = f"{type(self).__name__!r} does not support indexed access"
            raise KeyError(msg)
        if isinstance(getattr(type(self), key, None), TrackedParam) or hasattr(self, key):
            return getattr(self, key)
        msg = f"{type(self).__name__!r} has no attribute {key!r}"
        raise KeyError(msg)

    def __setitem__(self, key: str, value: object) -> None:
        """Set a value by name.

        Setting a value triggers invalidation of dependent constraints/costs.

        Args:
            key: Name of the TrackedParam or attribute
            value: New value to set

        Raises:
            KeyError: If the element has no value with this name that can be set

        """
        if not isinstance(getattr(type(self), key, None), TrackedParam) and not hasattr(self, key):
            msg = f"{type(self).__name__!r} has no attribute {key!r}"
            raise KeyError(msg)
        try:
            setattr(self, key, value)
        except AttributeError as err:
            msg = f"{type(self).__name__!r} attribute {key!r} cannot be set"
            raise KeyError(msg) from err

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def update_periods(self, periods: NDArray[np.float64]) -> None:
        """Set new period durations, invalidating everything that reads them."""
        self.periods = periods

    def extract_values(self, expr: LinearArray | None) -> tuple[float, ...]:
        """Evaluate each row of the expression in the current solution."""
        if expr is None:
            return ()
        return tuple(expr.value(self._solver.column_values()).tolist())

    def outputs(self) -> Mapping[OutputNameT, OutputData]:
        """Return the outputs the element reports, keyed by output name.

        Each declared output in the element's output names is read, and those
        that currently have a value are returned.
        """
        result: dict[OutputNameT, OutputData] = {}
        for output_name, method in self.declared_outputs():
            if output_name in self._output_names and (output_data := method.get_output(self)) is not None:
                result[output_name] = output_data  # type: ignore[assignment]  # name validated by `in` check at runtime
        return result

    def secondary_cost(self) -> LinearArray | None:
        """Return the element's time-preference objective, which breaks ties between equally cheap plans.

        Elements have none unless they move power between others, as connections do.
        """
        return None


class NetworkElement[OutputNameT: str](Element[OutputNameT]):
    """Element that participates in network power balance.

    Extends Element with connection tracking, power production/consumption
    protocol, and per-tag power balance constraints. Node and Battery inherit
    from this class. Connection inherits directly from Element.
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        output_names: frozenset[OutputNameT],
        is_source: bool = True,
        is_sink: bool = True,
        outbound_tags: set[int] | None = None,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a network element.

        Args:
            name: Name of the entity
            periods: Array of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints
            output_names: Frozenset of valid output names for this element type (used for type narrowing)
            is_source: Whether the element can produce power, so policies may draw from it
            is_sink: Whether the element can consume power, so policies may deliver to it
            outbound_tags: Tags that produced power can be placed on (None = all tags)
            inbound_tags: Tags that consumed power can draw from (None = all tags)

        """
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=output_names,
        )
        self._is_source = is_source
        self._is_sink = is_sink
        self._outbound_tags = None if outbound_tags is None else frozenset(outbound_tags)
        self._inbound_tags = None if inbound_tags is None else frozenset(inbound_tags)

        # Track connections for power balance
        self._connections: list[tuple[_ConnectionLike, Literal["source", "target"]]] = []

        # Lazily-created per-tag consumption decomposition variables
        self._consumed_by_tag: dict[int, LinearArray] | None = None

        # Lazily-created per-tag production decomposition variables
        self._produced_by_tag: dict[int, LinearArray] | None = None

    # The roles and tags shape the power balance rows and the per-tag variables,
    # which are created once, so they are fixed when the element is built

    @property
    def is_source(self) -> bool:
        """Return whether the element can produce power, so policies may draw from it."""
        return self._is_source

    @property
    def is_sink(self) -> bool:
        """Return whether the element can consume power, so policies may deliver to it."""
        return self._is_sink

    @property
    def outbound_tags(self) -> frozenset[int] | None:
        """Return the tags produced power can be placed on, or None for all tags."""
        return self._outbound_tags

    @property
    def inbound_tags(self) -> frozenset[int] | None:
        """Return the tags consumed power can draw from, or None for all tags."""
        return self._inbound_tags

    def register_connection(self, connection: _ConnectionLike, end: Literal["source", "target"]) -> None:
        """Register a connection to this element.

        Args:
            connection: The connection object
            end: Whether this element is the 'source' or 'target' of the connection

        """
        self._connections.append((connection, end))

    @property
    def outbound_connections(self) -> list[_ConnectionLike]:
        """Return the connections that carry power away from this element."""
        return [connection for connection, end in self._connections if end == "source"]

    @property
    def inbound_connections(self) -> list[_ConnectionLike]:
        """Return the connections that carry power into this element."""
        return [connection for connection, end in self._connections if end == "target"]

    # --- Element power protocol ---

    def element_power_produced(self) -> LinearArray | None:
        """Return this element's power production expression.

        Positive values represent power injected into the network.
        Production is placed on ``outbound_tags``.
        Override in subclasses.  Default returns None (no production).
        """
        return None

    def element_power_consumed(self) -> LinearArray | None:
        """Return this element's power consumption expression.

        Positive values represent power absorbed from the network.
        Consumption draws from ``inbound_tags``.
        Override in subclasses.  Default returns None (no consumption).
        """
        return None

    # --- Connection power queries ---

    def connection_power(self) -> LinearArray:
        """Return the net power from connections for all time periods.

        Positive means power flowing into this element from connections.
        Negative means power flowing out of this element to connections.
        """
        return LinearArray.sum_of(
            [
                LinearArray.zeros(self.n_periods),
                *(
                    conn.power_into_source if end == "source" else conn.power_into_target
                    for conn, end in self._connections
                ),
            ]
        )

    def connection_power_for_tag(self, tag: int) -> LinearArray:
        """Return the net power from connections for a specific tag."""
        return LinearArray.sum_of(
            [
                LinearArray.zeros(self.n_periods),
                *(
                    conn.power_into_source_for_tag(tag) if end == "source" else conn.power_into_target_for_tag(tag)
                    for conn, end in self._connections
                    if tag in conn.connection_tags()
                ),
            ]
        )

    def connection_tags(self) -> set[int]:
        """Return the union of all tags from all connected connections."""
        tags: set[int] = set()
        for conn, _end in self._connections:
            tags.update(conn.connection_tags())
        return tags

    # --- Power balance ---

    def _get_consumed_by_tag(self, inbound: set[int]) -> dict[int, LinearArray]:
        """Return per-tag consumption variables, creating them once on first call."""
        if self._consumed_by_tag is None:
            self._consumed_by_tag = {
                tag: self._solver.add_variables(self.n_periods, name=f"{self.name}.consumed_tag{tag}")
                for tag in sorted(inbound)
            }
        return self._consumed_by_tag

    def _get_produced_by_tag(self, outbound: set[int]) -> dict[int, LinearArray]:
        """Return per-tag production variables, creating them once on first call."""
        if self._produced_by_tag is None:
            self._produced_by_tag = {
                tag: self._solver.add_variables(self.n_periods, name=f"{self.name}.produced_tag{tag}")
                for tag in sorted(outbound)
            }
        return self._produced_by_tag

    def _tag_sets(self) -> tuple[set[int], set[int], set[int]]:
        """Return the connection tags and the tags production and consumption may use."""
        tags = self.connection_tags()
        outbound = set(tags) if self.outbound_tags is None else tags & self.outbound_tags
        inbound = set(tags) if self.inbound_tags is None else tags & self.inbound_tags
        return tags, outbound, inbound

    def _balance_count(self) -> int:
        """Return how many per-period balance blocks lead the power balance rows."""
        tags, outbound, inbound = self._tag_sets()
        return len(outbound | inbound) if tags else 1

    @constraint
    def element_power_balance(self) -> Rows:
        """Per-tag energy balance: for each tag, (connection + produced - consumed) * dt == 0.

        Formulated in energy units (kWh) so that shadow prices are $/kWh,
        independent of period width. Power (kW) is multiplied by the period
        duration (h) to give energy (kWh) for each balance constraint.

        Production is decomposed across ``outbound_tags`` via per-tag variables.
        Consumption is decomposed across ``inbound_tags`` via per-tag variables.
        Tags outside both sets are blocked (each connection's per-tag flow == 0).

        The rows start with one balance block per balanced tag, in tag order,
        followed by the decomposition blocks and the blocked connection rows,
        so ``power_balance_price`` can read the balance duals by position.
        Has no rows when there are no connections and no external power.
        """
        dt = self.periods  # hours per period
        tags, outbound, inbound = self._tag_sets()
        produced = self.element_power_produced()
        consumed = self.element_power_consumed()
        if not tags:
            if not self._connections and produced is None and consumed is None:
                return Rows.concat([])
            terms = [self.connection_power()]
            if produced is not None:
                terms.append(produced)
            if consumed is not None:
                terms.append(-consumed)
            return LinearArray.sum_of(terms) * dt == 0

        produced_by_tag = self._get_produced_by_tag(outbound) if produced is not None and outbound else {}
        consumed_by_tag = self._get_consumed_by_tag(inbound) if consumed is not None and inbound else {}

        # Per-tag power balance
        blocks: list[Rows] = []
        for tag in sorted(outbound | inbound):
            terms = [self.connection_power_for_tag(tag)]
            if tag in produced_by_tag:
                terms.append(produced_by_tag[tag])
            if tag in consumed_by_tag:
                terms.append(-consumed_by_tag[tag])
            blocks.append(LinearArray.sum_of(terms) * dt == 0)

        # Decompose production across outbound tags
        if produced is not None:
            blocks.append(LinearArray.sum_of([*produced_by_tag.values(), -produced]) * dt == 0)

        # Decompose consumption across inbound tags
        if consumed is not None:
            blocks.append(LinearArray.sum_of([*consumed_by_tag.values(), -consumed]) * dt == 0)

        # Tags outside both sets cannot pass through this element
        blocks.extend(
            (conn.power_into_source_for_tag(tag) if end == "source" else conn.power_into_target_for_tag(tag)) * dt == 0
            for tag in sorted(tags - outbound - inbound)
            for conn, end in self._connections
            if tag in conn.connection_tags()
        )

        return Rows.concat(blocks)

    def balance_rows(self) -> RowIndices | None:
        """Return the rows that balance each tag's power, or None when the balance does not apply.

        These lead the power balance rows, ahead of the rows that split production
        and consumption across tags and the rows that block tags from passing.
        An element whose connections carry only tags it blocks balances none.
        """
        rows = applied_constraint(self, "element_power_balance")
        balanced = self._balance_count()
        if rows is None or balanced == 0:
            return None
        return rows[: balanced * self.n_periods]

    @output(name=ELEMENT_POWER_BALANCE)
    def power_balance_price(self) -> OutputData | None:
        """Return the marginal cost of drawing one more kWh from this element in each period.

        Each balanced tag's dual is the cost of withdrawing a kWh of that tag here.
        An extra load draws whichever tag is cheapest, so the price is the lowest of them.
        """
        rows = self.balance_rows()
        if rows is None:
            return None
        duals = self._solver.row_duals()[rows]
        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit="$/kWh",
            values=tuple(duals.reshape(-1, self.n_periods).min(axis=0).tolist()),
        )
