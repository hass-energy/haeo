"""Connection element for unidirectional power flow between nodes.

A Connection represents a single direction of power flow from source to target.
Bidirectional paths are modelled as two separate connections.

Connection creates LP variables for the power flow, then chains them through
segments. Each segment may add constraints, costs, or transform the expression.
"""

from collections import OrderedDict
from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import output

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
    segments: NotRequired[dict[str, SegmentSpec]]


class Connection[TOutputName: str](Element[TOutputName]):
    """Unidirectional power flow from source to target.

    Creates LP variables for the flow, chains them through segments.
    power_in is the flow entering the connection at the source end.
    power_out is the flow exiting at the target end (after segment transforms).
    """

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        source: str,
        target: str,
        segments: dict[str, SegmentSpec] | None = None,
        output_names: frozenset[TOutputName] | None = None,
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

        self._segment_specs: OrderedDict[str, SegmentSpec] = OrderedDict(segments or {})
        self._segments: OrderedDict[str, Segment] = OrderedDict()

        # Power flow variables and chain output (set during initialization)
        self._power_in: HighspyArray | None = None
        self._power_out: HighspyArray | None = None

    @property
    def segments(self) -> OrderedDict[str, Segment]:
        """Return the ordered dict of segments."""
        return self._segments

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
        self._power_in = self._solver.addVariables(
            self.n_periods,
            lb=0,
            name_prefix=f"{self.name}_",
            out_array=True,
        )

        specs = list(self._segment_specs.items()) or [("passthrough", {"segment_type": "passthrough"})]

        flow = self._power_in
        for seg_name, seg_spec in specs:
            seg = create_segment(
                segment_id=f"{self.name}_{seg_name}",
                n_periods=self.n_periods,
                periods=self.periods,
                solver=self._solver,
                spec=seg_spec,
                source_element=source_element,
                target_element=target_element,
                power_in=flow,
            )
            self._segments[seg_name] = seg
            flow = seg.power_out
        self._power_out = flow

    @property
    def power_in(self) -> HighspyArray:
        """Power entering the connection at the source end (LP variables)."""
        assert self._power_in is not None  # noqa: S101
        return self._power_in

    @property
    def power_out(self) -> HighspyArray:
        """Power exiting the connection at the target end (after transforms)."""
        assert self._power_out is not None  # noqa: S101
        return self._power_out

    # --- Node power balance interface ---

    @property
    def power_into_source(self) -> HighspyArray:
        """Power flowing into the source node from this connection.

        For unidirectional connections, the source node loses power_in
        (power flows away from source into the connection).
        """
        return -self._power_in

    @property
    def power_into_target(self) -> HighspyArray:
        """Power flowing into the target node from this connection.

        For unidirectional connections, the target node gains power_out
        (power flows from the connection into the target).
        """
        return self._power_out

    # --- Constraint and cost delegation to segments ---

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Collect constraints from all segments."""
        result: dict[str, highs_cons | list[highs_cons]] = {}
        for segment in self._segments.values():
            for name, cons in segment.constraints().items():
                result[f"{segment.segment_id}_{name}"] = cons
        own_constraints = super().constraints()
        result.update(own_constraints)
        return result

    def cost(self) -> Any:  # type: ignore[override]
        """Aggregate costs from all segments."""
        costs = [sc for seg in self._segments.values() if (sc := seg.cost()) is not None]
        if not costs:
            return None
        if len(costs) == 1:
            return costs[0]
        return Highs.qsum(costs)

    # --- Output methods ---

    def _segment_outputs(self) -> dict[str, dict[str, OutputData]]:
        """Collect outputs from all segments."""
        result: dict[str, dict[str, OutputData]] = {}
        for seg_name, segment in self._segments.items():
            seg_outputs = segment.outputs()
            if seg_outputs:
                result[seg_name] = seg_outputs
        return result

    @output
    def connection_power(self) -> OutputData:
        """Power flow through this connection."""
        return OutputData(
            type=OutputType.POWER_FLOW,
            unit="kW",
            values=self.extract_values(self.power_in),
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
