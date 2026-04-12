"""Connection element for power flow between nodes.

Connection composes multiple segments (efficiency, power limits, pricing)
to model various connection behaviors.
"""

from collections import OrderedDict
from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import output

from .segments import Segment, SegmentSpec, create_segment

type ConnectionElementTypeName = Literal["connection"]
# Model element type for connections
ELEMENT_TYPE: Final[ConnectionElementTypeName] = "connection"


class ConnectionElementConfig(TypedDict):
    """Configuration for Connection model elements."""

    element_type: ConnectionElementTypeName
    name: str
    source: str
    target: str
    mirror_segment_order: NotRequired[bool]
    segments: NotRequired[dict[str, SegmentSpec]]


# Minimum segments needed before linking is required
MIN_SEGMENTS_FOR_LINKING = 2


type ConnectionOutputName = Literal[
    "connection_power_source_target",
    "connection_power_target_source",
    "segments",
]

CONNECTION_POWER_SOURCE_TARGET: Final = "connection_power_source_target"
CONNECTION_POWER_TARGET_SOURCE: Final = "connection_power_target_source"
CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: Final = "connection_shadow_power_max_source_target"
CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: Final = "connection_shadow_power_max_target_source"
CONNECTION_SEGMENTS: Final = "segments"

type ConnectionSegmentOutputs = dict[str, dict[str, OutputData]]
type ConnectionOutputValue = OutputData | ConnectionSegmentOutputs

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_SOURCE_TARGET,
        CONNECTION_POWER_TARGET_SOURCE,
        CONNECTION_SEGMENTS,
    )
)


class Connection[TOutputName: str](Element[TOutputName]):
    """Connection element for power flow between nodes.

    Segments are provided as a mapping of segment names to specifications:
    - segment name (dict key): Used to name the segment in the connection
    - segment_type: One of "efficiency", "passthrough", "power_limit", "pricing"
    - Additional kwargs specific to the segment type

    Segments are chained in the order provided. The connection links adjacent
    segments by constraining their output to the next segment's input.

    Source→target flow always uses the order provided.
    Target→source flow uses the reverse order by default.
    Enable `mirror_segment_order` to use the same segment order for both flow directions.

    For parameter updates, access segments via indexing:
        connection["power_limit"].max_power_source_target = new_value
        connection[0].max_power_source_target = new_value  # by index

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
        mirror_segment_order: bool = False,
        output_names: frozenset[TOutputName] | None = None,
    ) -> None:
        """Initialize a connection.

        Args:
            name: Name of the connection
            periods: Array of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints
            source: Name of the source element
            target: Name of the target element
            segments: Dict of segment names to SegmentSpec TypedDicts.
                Each spec has segment_type plus segment-specific parameters.
            mirror_segment_order: Use the same segment order for both flow directions.
            output_names: Output names for this connection type

        """
        # Use provided output_names or default to CONNECTION_OUTPUT_NAMES
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
        self._mirror_segment_order = mirror_segment_order

        # Segments stored in OrderedDict for name-based and index-based access
        self._segment_specs: OrderedDict[str, SegmentSpec] = OrderedDict(segments or {})
        self._segments: OrderedDict[str, Segment] = OrderedDict()

        # Outputs of each directional chain (set during initialization)
        self._st_output: HighspyArray | None = None
        self._ts_output: HighspyArray | None = None

    @property
    def segments(self) -> OrderedDict[str, Segment]:
        """Return the ordered dict of segments."""
        return self._segments

    def set_endpoints(self, source_element: Element[Any], target_element: Element[Any]) -> None:
        """Set source/target element references on the connection segments."""
        self._source_element = source_element
        self._target_element = target_element
        if not self._segments:
            self._initialize_segments(source_element, target_element)

    def _initialize_segments(self, source_element: Element[Any], target_element: Element[Any]) -> None:
        # Create the connection's power flow variables
        self._power_st = self._solver.addVariables(
            self.n_periods,
            lb=0,
            name_prefix=f"{self.name}_st_",
            out_array=True,
        )
        self._power_ts = self._solver.addVariables(
            self.n_periods,
            lb=0,
            name_prefix=f"{self.name}_ts_",
            out_array=True,
        )

        # Build segment specs list
        specs = list(self._segment_specs.items())
        if not specs:
            specs = [("passthrough", {"segment_type": "passthrough"})]

        # Determine segment order for each direction
        st_specs = specs
        ts_specs = specs if self._mirror_segment_order else list(reversed(specs))

        # Build source→target chain
        flow = self._power_st
        for segment_name, segment_spec in st_specs:
            resolved = self._resolve_segment_name(segment_name, "st")
            seg = create_segment(
                segment_id=f"{self.name}_{resolved}",
                n_periods=self.n_periods,
                periods=self.periods,
                solver=self._solver,
                spec=segment_spec,
                source_element=source_element,
                target_element=target_element,
                power_in=flow,
                direction="st",
            )
            self._segments[resolved] = seg
            flow = seg.power_out
        self._st_output = flow

        # Build target→source chain
        # Skip segment types that are not directional (e.g., soc_pricing operates
        # on battery state, not power direction) to avoid duplicate costs.
        _NON_DIRECTIONAL = {"soc_pricing"}
        flow = self._power_ts
        for segment_name, segment_spec in ts_specs:
            if segment_spec["segment_type"] in _NON_DIRECTIONAL:
                continue
            resolved = self._resolve_segment_name(segment_name, "ts")
            seg = create_segment(
                segment_id=f"{self.name}_{resolved}",
                n_periods=self.n_periods,
                periods=self.periods,
                solver=self._solver,
                spec=segment_spec,
                source_element=source_element,
                target_element=target_element,
                power_in=flow,
                direction="ts",
            )
            self._segments[resolved] = seg
            flow = seg.power_out
        self._ts_output = flow

    def _resolve_segment_name(self, base_name: str, suffix: str) -> str:
        """Generate a unique segment name."""
        name = f"{base_name}_{suffix}"
        counter = 0
        while name in self._segments:
            counter += 1
            name = f"{base_name}_{suffix}_{counter}"
        return name

    @property
    def power_source_target(self) -> HighspyArray:
        """Total power flowing from source to target."""
        return self._power_st

    @property
    def power_target_source(self) -> HighspyArray:
        """Total power flowing from target to source."""
        return self._power_ts

    @property
    def power_into_source(self) -> HighspyArray:
        """Effective power flowing into the source element."""
        return self._ts_output - self._power_st

    @property
    def power_into_target(self) -> HighspyArray:
        """Effective power flowing into the target element."""
        return self._st_output - self._power_ts

    # --- Segment linking constraints ---

    # Segment linking is no longer needed — segments chain via apply().
    # The Connection creates variables, passes them through segments,
    # and segments add constraints/costs as side effects.

    # --- Output methods ---

    def _segment_outputs(self) -> ConnectionSegmentOutputs:
        """Collect outputs from all segments."""
        segment_outputs: ConnectionSegmentOutputs = {}

        for segment_name, segment in self._segments.items():
            outputs = segment.outputs()
            if outputs:
                segment_outputs[segment_name] = outputs

        return segment_outputs

    @output
    def connection_power_source_target(self) -> OutputData:
        """Power flow from source to target."""
        return OutputData(
            type=OutputType.POWER_FLOW,
            unit="kW",
            values=self.extract_values(self.power_source_target),
            direction="+",
        )

    @output
    def connection_power_target_source(self) -> OutputData:
        """Power flow from target to source."""
        return OutputData(
            type=OutputType.POWER_FLOW,
            unit="kW",
            values=self.extract_values(self.power_target_source),
            direction="-",
        )

    @output(name=CONNECTION_SEGMENTS)
    def segment_outputs(self) -> ConnectionSegmentOutputs | None:
        """Return outputs grouped by segment."""
        segment_outputs = self._segment_outputs()
        return segment_outputs or None


__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_SEGMENTS",
    "CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET",
    "CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputName",
    "ConnectionOutputValue",
    "ConnectionSegmentOutputs",
]
