"""Connection element for unidirectional power flow between nodes.

A Connection represents a single direction of power flow from source to target.
Bidirectional paths are modelled as two separate connections.

Connection creates per-tag LP variables for the power flow, then chains them
through segments. Each segment receives and returns a dict of per-tag flows.
"""

from collections import OrderedDict
from functools import reduce
import operator
from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import output
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segments import Segment, SegmentSpec, create_segment

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
    tag_costs: NotRequired[list[dict[str, Any]]]


class Connection[TOutputName: str](Element[TOutputName]):
    """Unidirectional power flow from source to target.

    Creates per-tag LP variables for the flow and chains them through segments.
    power_in is the per-tag flow entering the connection at the source end.
    power_out is the per-tag flow exiting at the target end (after segment transforms).
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        source: str,
        target: str,
        is_external: bool = False,
        is_time_sensitive: bool = False,
        segments: dict[str, SegmentSpec] | None = None,
        output_names: frozenset[TOutputName] | None = None,
        tags: set[int] | None = None,
        tag_costs: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize a unidirectional connection."""
        actual_output_names: frozenset[Any] = output_names if output_names is not None else CONNECTION_OUTPUT_NAMES
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

        # Per-tag power flows (set during initialization)
        # Default to a single tag (0) when no tags specified — always-tagged paradigm
        self._tags: set[int] = set(tags) if tags else {0}
        self._tag_costs: list[dict[str, Any]] = tag_costs or []
        self._power_in: dict[int, HighspyArray] = {}
        self._power_out: dict[int, HighspyArray] = {}

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
        flows: dict[int, HighspyArray] = {}
        for tag in sorted(self._tags):
            flows[tag] = self._solver.addVariables(
                self.n_periods,
                lb=0,
                name_prefix=f"{self.name}_t{tag}_",
                out_array=True,
            )
        self._power_in = dict(flows)

        specs = list(self._segment_specs.items()) or [("passthrough", {"segment_type": "passthrough"})]

        for seg_name, seg_spec in specs:
            seg = create_segment(
                segment_id=f"{self.name}_{seg_name}",
                n_periods=self.n_periods,
                periods=self.periods,
                solver=self._solver,
                spec=seg_spec,
                source_element=source_element,
                target_element=target_element,
                power_in=flows,
            )
            self._segments[seg_name] = seg
            flows = seg.power_out

        self._power_out = flows

    @property
    def power_in(self) -> dict[int, HighspyArray]:
        """Per-tag power entering the connection at the source end."""
        return self._power_in

    @property
    def total_power_in(self) -> HighspyArray:
        """Total power entering the connection (sum of all tags)."""
        return reduce(operator.add, self._power_in.values())

    @property
    def power_out(self) -> dict[int, HighspyArray]:
        """Per-tag power exiting the connection at the target end."""
        return self._power_out

    @property
    def total_power_out(self) -> HighspyArray:
        """Total power exiting the connection (sum of all tags)."""
        return reduce(operator.add, self._power_out.values())

    def connection_tags(self) -> set[int]:
        """Return the set of tags on this connection."""
        return self._tags

    def power_into_source_for_tag(self, tag: int) -> HighspyArray:
        """Power flowing into the source node for a specific tag."""
        return -self._power_in[tag]

    def power_into_target_for_tag(self, tag: int) -> HighspyArray:
        """Power flowing into the target node for a specific tag."""
        return self._power_out[tag]

    # --- Node power balance interface ---

    @property
    def power_into_source(self) -> HighspyArray:
        """Power flowing into the source node from this connection.

        For unidirectional connections, the source node loses power_in
        (power flows away from source into the connection).
        """
        return -self.total_power_in

    @property
    def power_into_target(self) -> HighspyArray:
        """Power flowing into the target node from this connection.

        For unidirectional connections, the target node gains power_out
        (power flows from the connection into the target).
        """
        return self.total_power_out

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Collect constraints from all segments."""
        result: dict[str, highs_cons | list[highs_cons]] = {}
        for segment in self._segments.values():
            for name, cons in segment.constraints().items():
                result[f"{segment.segment_id}_{name}"] = cons
        own_constraints = super().constraints()
        result.update(own_constraints)
        return result

    def cost(self) -> tuple[highs_linear_expression | None, highs_linear_expression]:  # type: ignore[override]
        """Return (primary_cost, secondary_cost) for this connection.

        Primary: segment costs + tag costs.
        Secondary: time-preference objective for deterministic ordering.
        """
        primary_costs: list[highs_linear_expression] = [
            sc for seg in self._segments.values() if (sc := seg.cost()) is not None
        ]

        for tc in self._tag_costs:
            tag = tc["tag"]
            price = broadcast_to_sequence(tc.get("price"), self.n_periods)
            if price is not None and tag in self._power_in:
                primary_costs.append(Highs.qsum(self._power_in[tag] * price * self.periods))

        primary = None
        if primary_costs:
            primary = primary_costs[0] if len(primary_costs) == 1 else Highs.qsum(primary_costs)

        # Time-preference objective: prefer earlier energy transfer
        n = self.n_periods
        weights = self.priority * n + np.arange(1, n + 1, dtype=np.float64)
        secondary = Highs.qsum(self.total_power_in * self.periods * weights)

        if primary is None:
            return (None, secondary)
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
        """Power flow through this connection."""
        return OutputData(
            type=OutputType.POWER_FLOW,
            unit="kW",
            values=self.extract_values(self.total_power_in),
            direction="+",
            priority=self.priority,
        )

    @output(name=CONNECTION_SEGMENTS)
    def segment_outputs(self) -> dict[str, dict[str, OutputData]] | None:
        """Return outputs grouped by segment."""
        outputs = self._segment_outputs()
        return outputs or None

    def __getitem__(self, key: str | int) -> Any:
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
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputName",
]
