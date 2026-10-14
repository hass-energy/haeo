"""Connection element for unidirectional power flow between nodes.

A Connection represents a single direction of power flow from source to target.
Bidirectional paths are modelled as two separate connections.

Connection creates per-tag LP variables for the power flow, then chains them
through segments. Each segment derives its per-tag input flow from the segment
before it, so the flow leaving the connection always reflects the current
segment parameters.
"""

from collections import OrderedDict
from math import isqrt
from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the network's connection endpoints,
    # which can be any concrete NetworkElement subtype (Battery, Node, ...). Element is invariant
    # in its output-name Literal (see element.py's outputs()), so no non-Any type can express
    # "an Element of some unknown output-name type" across this dynamically-typed registry.
    Final,
    Literal,
    NotRequired,
    TypedDict,
)

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import LinearArray, total
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import output
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util.solver_rows import RowIndices

from .segments import FlowProvider, FlowVariables, PowerLimitSegment, Segment, SegmentSpec, create_segment

type ConnectionElementTypeName = Literal["connection"]
# Model element type for connection strings
ELEMENT_TYPE: Final[ConnectionElementTypeName] = "connection"

type ConnectionOutputName = Literal[
    "connection_power",
    "segments",
]

CONNECTION_POWER: Final = "connection_power"
CONNECTION_SEGMENTS: Final = "segments"

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset((CONNECTION_POWER, CONNECTION_SEGMENTS))

# Largest perturbation added to a time-preference weight. Distinct weights differ by
# at least one, so a perturbation below half of that never reorders two of them.
TIE_BREAK_SCALE: Final = 0.5


class _Primes:
    """The primes in order, extended as more are needed."""

    def __init__(self) -> None:
        self._primes = np.array([2, 3, 5, 7, 11, 13], dtype=np.int64)

    def first(self, count: int) -> NDArray[np.int64]:
        """Return the first ``count`` primes."""
        limit = 2 * int(self._primes[-1])
        while len(self._primes) < count:
            limit *= 2
            sieve = np.ones(limit, dtype=bool)
            sieve[:2] = False
            for factor in range(2, isqrt(limit) + 1):
                if sieve[factor]:
                    sieve[factor * factor :: factor] = False
            self._primes = np.flatnonzero(sieve)
        return self._primes[:count]


_PRIMES = _Primes()


def tie_break_perturbation(priority: int, n_periods: int) -> NDArray[np.float64]:
    """Return a fixed value in [0, 1) for each period of a connection.

    The time-preference weight is a connection term plus a period term, so moving
    energy between two connections in opposite directions across two periods leaves
    it unchanged, and equally cheap plans that differ only by such swaps would be
    chosen by the order of the solver's rows. Adding a value that no combination of
    other values can cancel gives every such exchange a cost, so one plan is
    preferred. An exchange whose cost is smaller than the solver's tolerance is
    still decided by the solver, so this makes exact ties impossible rather than
    every exchange decisive.

    Each connection and period has its own prime, and its value is the fractional
    part of that prime's square root. Square roots of distinct primes are linearly
    independent over the rationals, together with one, so no weighted sum of these
    values with rational weights is zero unless every weight is. A single irrational
    such as the golden ratio is not enough: every fractional part of a multiple of
    it is a whole number plus a multiple of the same irrational, so sums of them can
    cancel exactly.

    The prime is chosen by the Cantor pairing of priority and period, which does not
    depend on the horizon length, so each period keeps its value as the horizon
    changes.
    """
    period = np.arange(n_periods, dtype=np.int64)
    index = (priority + period) * (priority + period + 1) // 2 + period
    primes = _PRIMES.first(int(index.max(initial=0)) + 1)
    return np.mod(np.sqrt(primes[index].astype(np.float64)), 1.0)


class ConnectionElementConfig(TypedDict):
    """Configuration for Connection model elements."""

    element_type: ConnectionElementTypeName
    name: str
    source: str
    target: str
    is_external: NotRequired[bool]
    is_time_sensitive: NotRequired[bool]
    segments: NotRequired[dict[str, SegmentSpec]]
    tags: NotRequired[set[int]]


class Connection[TOutputName: str](Element[TOutputName]):
    """Unidirectional power flow from source to target.

    Creates per-tag LP variables for the flow and chains them through segments.
    power_in is the per-tag flow entering the connection at the source end.
    power_out is the per-tag flow exiting at the target end (after segment transforms).
    measured_power is the per-tag flow at the connection's measured point, where its
    power limit applies; prices and reported power refer to the same flow.
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        source: str,
        target: str,
        is_external: bool = False,
        is_time_sensitive: bool = False,
        segments: dict[str, SegmentSpec] | None = None,
        output_names: frozenset[TOutputName] | None = None,
        tags: set[int],
    ) -> None:
        """Initialize a unidirectional connection."""

        actual_output_names: frozenset[TOutputName] = (
            output_names if output_names is not None else CONNECTION_OUTPUT_NAMES  # type: ignore[assignment]  # default output names are only valid when TOutputName is (a superset of) ConnectionOutputName, which holds for every real construction path (Network.add()'s overload pins TOutputName=ConnectionOutputName)
        )
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=actual_output_names,
        )
        self._source = source
        self._target = target
        self._source_element: Element[Any] | None = None
        self._target_element: Element[Any] | None = None
        self.is_external = is_external
        self.is_time_sensitive = is_time_sensitive
        self.priority = 0  # assigned by Network from sort_key

        self._segment_specs: OrderedDict[str, SegmentSpec] = OrderedDict(segments or {})
        self._segments: OrderedDict[str, Segment] = OrderedDict()

        self._tags: set[int] = set(tags)
        self._power_in: dict[int, LinearArray] = {}

    @property
    def segments(self) -> OrderedDict[str, Segment]:
        """Return the ordered dict of segments."""
        return self._segments

    @property
    def sort_key(self) -> tuple[bool, bool, str, str, str]:
        """Deterministic sort key for time-preference ordering.

        Prefers own power over external, then time-sensitive over invariant,
        then alphabetical by source/target/name for tiebreaking.
        """
        return (self.is_external, not self.is_time_sensitive, self._source, self._target, self.name)

    @property
    def source(self) -> str:
        """Return the name of the source element."""
        return self._source

    @property
    def target(self) -> str:
        """Return the name of the target element."""
        return self._target

    def set_endpoints(self, source_element: Element[Any], target_element: Element[Any]) -> None:
        """Set source/target element references and build the segment chain."""
        self._source_element = source_element
        self._target_element = target_element
        if not self._segments:
            self._initialize_segments(source_element, target_element)

    def _initialize_segments(self, source_element: Element[Any], target_element: Element[Any]) -> None:
        # Create per-tag LP variables
        self._power_in = {
            tag: self._solver.add_variables(self.n_periods, name=f"{self.name}.power_in_tag{tag}")
            for tag in sorted(self._tags)
        }

        specs = list(self._segment_specs.items()) or [("passthrough", {"segment_type": "passthrough"})]

        # Each segment reads its input from the one before it. The measured point is
        # the flow entering the power limit segment, or the variables when there is none.
        upstream: FlowProvider = FlowVariables(self._power_in)
        self._measured: FlowProvider = upstream
        for seg_name, seg_spec in specs:
            seg = create_segment(
                segment_id=f"{self.name}_{seg_name}",
                n_periods=self.n_periods,
                periods=self.periods,
                solver=self._solver,
                spec=seg_spec,
                source_element=source_element,
                target_element=target_element,
                upstream=upstream,
            )
            self._segments[seg_name] = seg
            if isinstance(seg, PowerLimitSegment):
                self._measured = upstream
            upstream = seg
        self._output: FlowProvider = upstream

    @property
    def power_in(self) -> dict[int, LinearArray]:
        """Per-tag power entering the connection at the source end."""
        return self._power_in

    @property
    def total_power_in(self) -> LinearArray:
        """Total power entering the connection (sum of all tags)."""
        return LinearArray.sum_of(self._power_in.values())

    @property
    def power_out(self) -> dict[int, LinearArray]:
        """Per-tag power exiting the connection at the target end, derived from the last segment."""
        return self._output.power_out

    @property
    def total_power_out(self) -> LinearArray:
        """Total power exiting the connection (sum of all tags)."""
        return LinearArray.sum_of(self.power_out.values())

    @property
    def measured_power(self) -> dict[int, LinearArray]:
        """Per-tag power at the connection's measured point.

        The measured point is the flow entering the power limit segment, so the
        limit, policy prices and reported power all refer to the same flow, and
        efficiency losses fall on the other side of it. A connection without a
        power limit has no losses to place it against and is measured where
        power enters it.
        """
        return self._measured.power_out

    @property
    def total_measured_power(self) -> LinearArray:
        """Total power at the measured point (sum of all tags)."""
        return LinearArray.sum_of(self.measured_power.values())

    def connection_tags(self) -> set[int]:
        """Return the set of tags on this connection."""
        return self._tags

    def power_into_source_for_tag(self, tag: int) -> LinearArray:
        """Power flowing into the source node for a specific tag."""
        return -self._power_in[tag]

    def power_into_target_for_tag(self, tag: int) -> LinearArray:
        """Power flowing into the target node for a specific tag."""
        return self.power_out[tag]

    # --- Node power balance interface ---

    @property
    def power_into_source(self) -> LinearArray:
        """Power flowing into the source node from this connection.

        For unidirectional connections, the source node loses power_in
        (power flows away from source into the connection).
        """
        return -self.total_power_in

    @property
    def power_into_target(self) -> LinearArray:
        """Power flowing into the target node from this connection.

        For unidirectional connections, the target node gains power_out
        (power flows from the connection into the target).
        """
        return self.total_power_out

    def constraints(self) -> dict[str, RowIndices]:
        """Collect constraints from all segments."""
        result: dict[str, RowIndices] = {}
        for segment in self._segments.values():
            for name, cons in segment.constraints().items():
                result[f"{segment.segment_id}_{name}"] = cons
        own_constraints = super().constraints()
        result.update(own_constraints)
        return result

    def cost(self) -> tuple[LinearArray | None, LinearArray]:  # type: ignore[override]
        """Return (primary_cost, secondary_cost) for this connection.

        Primary: segment costs.
        Secondary: time-preference objective for deterministic ordering.
        """
        primary = total([seg.cost() for seg in self._segments.values()])

        # Time-preference objective: prefer earlier energy transfer, perturbed so that
        # equally cheap plans never tie
        n = self.n_periods
        weights = (
            self.priority * n
            + np.arange(1, n + 1, dtype=np.float64)
            + TIE_BREAK_SCALE * tie_break_perturbation(self.priority, n)
        )
        secondary = (self.total_measured_power * self.periods * weights).total()

        return (primary, secondary)

    # --- Output methods ---

    def _segment_outputs(self) -> dict[str, dict[str, OutputData]]:
        """Collect outputs from all segments."""
        result: dict[str, dict[str, OutputData]] = {}
        for seg_name, segment in self._segments.items():
            seg_outputs = segment.outputs()
            if seg_outputs:
                result[seg_name] = seg_outputs
        return result

    @output(name=CONNECTION_POWER)
    def _connection_power_output(self) -> OutputData:
        """Power at the connection's measured point, where its power limit applies."""
        return OutputData(
            type=OutputType.POWER_FLOW,
            unit="kW",
            values=self.extract_values(self.total_measured_power),
            direction="+",
            priority=self.priority,
        )

    @output(name=CONNECTION_SEGMENTS)
    def segment_outputs(self) -> dict[str, dict[str, OutputData]] | None:
        """Return outputs grouped by segment."""
        outputs = self._segment_outputs()
        return outputs or None

    def __getitem__(self, key: str | int) -> object:
        """Look up segments by name or index."""
        if isinstance(key, int):
            try:
                return list(self._segments.values())[key]
            except IndexError as exc:
                msg = f"No segment at index {key}"
                raise KeyError(msg) from exc
        if key in self._segments:
            return self._segments[key]
        return super().__getitem__(key)


__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER",
    "CONNECTION_SEGMENTS",
    "ELEMENT_TYPE",
    "TIE_BREAK_SCALE",
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputName",
    "tie_break_perturbation",
]
