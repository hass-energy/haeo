"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping
from typing import Final, Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from .linear import LinearArray, Rows, total
from .output_data import OutputData
from .reactive import OutputMethod, ReactiveConstraint, ReactiveCost, TrackedParam, applied_constraint, constraint, cost
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

    def __setitem__(self, key: str, value: object) -> None:
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

    def extract_values(self, expr: LinearArray | None) -> tuple[float, ...]:
        """Evaluate each row of the expression in the current solution."""
        if expr is None:
            return ()
        return tuple(expr.value(self._solver.column_values()).tolist())

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

    def constraints(self) -> dict[str, RowIndices]:
        """Return all constraints from this element.

        Discovers and calls all @constraint decorated methods. Calling the methods
        triggers automatic constraint creation/updating in the solver via decorators.

        Returns:
            Dictionary mapping constraint method names to the solver rows they hold

        """
        result: dict[str, RowIndices] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, ReactiveConstraint):
                # Call the constraint method to trigger decorator lifecycle
                method = getattr(self, name)
                method()
                if (cons := applied_constraint(self, name)) is not None:
                    result[name] = cons
        return result

    @cost
    def cost(self) -> LinearArray | None:
        """Return aggregated primary cost expression from this element.

        Discovers and calls all @cost decorated methods, summing their results
        into a single expression. Cached by the @cost decorator — only
        recomputes when underlying @cost method dependencies change.
        """
        # Access the decorator's internal name to skip self in the dir() loop.
        # _name is set by ReactiveCost.__set_name__ and is not part of the public API.
        this_method_name = type(self).cost._name  # type: ignore[attr-defined]  # noqa: SLF001 (_name is set by ReactiveCost.__set_name__, not part of public API)

        costs: list[LinearArray] = []
        for name in dir(type(self)):
            if name == this_method_name:
                continue
            attr = getattr(type(self), name, None)
            if not isinstance(attr, ReactiveCost):
                continue

            method = getattr(self, name)
            if (cost_value := method()) is not None:
                costs.append(cost_value)

        return total(costs)


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
        self._connections: list[tuple[_ConnectionLike, Literal["source", "target"]]] = []

        # Lazily-created per-tag consumption decomposition variables
        self._consumed_by_tag: dict[int, LinearArray] | None = None

        # Lazily-created per-tag production decomposition variables
        self._produced_by_tag: dict[int, LinearArray] | None = None

    def register_connection(self, connection: _ConnectionLike, end: Literal["source", "target"]) -> None:
        """Register a connection to this element.

        Args:
            connection: The connection object
            end: Whether this element is the 'source' or 'target' of the connection

        """
        self._connections.append((connection, end))

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

    @constraint(output=True, unit="$/kWh")
    def element_power_balance(self) -> Rows:
        """Per-tag energy balance: for each tag, (connection + produced - consumed) * dt == 0.

        Formulated in energy units (kWh) so that shadow prices are $/kWh,
        independent of period width. Power (kW) is multiplied by the period
        duration (h) to give energy (kWh) for each balance constraint.

        Production is decomposed across ``outbound_tags`` via per-tag variables.
        Consumption is decomposed across ``inbound_tags`` via per-tag variables.
        Tags outside both sets are blocked (each connection's per-tag flow == 0).

        Output: shadow price indicating the marginal value of energy at this element.
        Has no rows when there are no connections and no external power.
        """
        dt = self.periods  # hours per period
        tags = self.connection_tags()
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

        # Determine which tags can carry produced/consumed power
        outbound = set(tags) if self.outbound_tags is None else (self.outbound_tags & tags)
        inbound = set(tags) if self.inbound_tags is None else (self.inbound_tags & tags)

        blocks: list[Rows] = []

        # Decompose production across outbound tags
        produced_by_tag: dict[int, LinearArray] = {}
        if produced is not None:
            if outbound:
                produced_by_tag = self._get_produced_by_tag(outbound)
                blocks.append(LinearArray.sum_of([*produced_by_tag.values(), -produced]) * dt == 0)
            else:
                blocks.append(produced * dt == 0)

        # Decompose consumption across inbound tags
        consumed_by_tag: dict[int, LinearArray] = {}
        if consumed is not None:
            if inbound:
                consumed_by_tag = self._get_consumed_by_tag(inbound)
                blocks.append(LinearArray.sum_of([*consumed_by_tag.values(), -consumed]) * dt == 0)
            else:
                blocks.append(consumed * dt == 0)

        # Per-tag power balance
        for tag in sorted(tags):
            if tag in outbound or tag in inbound:
                terms = [self.connection_power_for_tag(tag)]
                if tag in produced_by_tag:
                    terms.append(produced_by_tag[tag])
                if tag in consumed_by_tag:
                    terms.append(-consumed_by_tag[tag])
                blocks.append(LinearArray.sum_of(terms) * dt == 0)
            else:
                blocks.extend(
                    (conn.power_into_source_for_tag(tag) if end == "source" else conn.power_into_target_for_tag(tag))
                    * dt
                    == 0
                    for conn, end in self._connections
                    if tag in conn.connection_tags()
                )

        return Rows.concat(blocks)
