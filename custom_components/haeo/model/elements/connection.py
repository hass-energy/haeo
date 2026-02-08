"""Connection element for power flow between nodes.

Connection composes multiple segments (efficiency, power limits, pricing)
to model various connection behaviors.
"""

from collections import OrderedDict
from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.objective import ObjectiveCost, as_objective_cost, combine_objectives
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import constraint, output
from custom_components.haeo.model.util import time_preference_weights

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
CONNECTION_TIME_SLICE: Final = "connection_time_slice"
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

        # Segments stored in OrderedDict for name-based and index-based access
        self._segment_specs: OrderedDict[str, SegmentSpec] = OrderedDict(segments or {})
        self._segments: OrderedDict[str, Segment] = OrderedDict()

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
        segment_specs = self._segment_specs
        for idx, (segment_name, segment_spec) in enumerate(segment_specs.items()):
            # Ensure unique segment names
            resolved_name = segment_name
            if resolved_name in self._segments:
                resolved_name = f"{resolved_name}_{idx}"

            # Create segment with standard args plus spec
            segment_id = f"{self.name}_{resolved_name}"
            segment = create_segment(
                segment_id=segment_id,
                n_periods=self.n_periods,
                periods=self.periods,
                solver=self._solver,
                spec=segment_spec,
                source_element=source_element,
                target_element=target_element,
            )
            self._segments[resolved_name] = segment

        # If no segments provided, create a passthrough segment
        if not self._segments:
            self._segments["passthrough"] = create_segment(
                segment_id=f"{self.name}_passthrough",
                n_periods=self.n_periods,
                periods=self.periods,
                solver=self._solver,
                spec={"segment_type": "passthrough"},
                source_element=source_element,
                target_element=target_element,
            )

    @property
    def _first(self) -> Segment:
        """Return the first segment in the chain."""
        if not self._segments:
            msg = f"{type(self).__name__} has no segments configured"
            raise RuntimeError(msg)
        return next(iter(self._segments.values()))

    @property
    def _last(self) -> Segment:
        """Return the last segment in the chain."""
        if not self._segments:
            msg = f"{type(self).__name__} has no segments configured"
            raise RuntimeError(msg)
        return next(reversed(self._segments.values()))

    @property
    def source(self) -> str:
        """Return the name of the source element."""
        return self._source

    @property
    def target(self) -> str:
        """Return the name of the target element."""
        return self._target

    @property
    def power_source_target(self) -> HighspyArray:
        """Return power flowing from source to target (input to first segment)."""
        return self._first.power_in_st

    @property
    def power_target_source(self) -> HighspyArray:
        """Return power flowing from target to source (input to first segment from t→s direction)."""
        return self._first.power_in_ts

    @property
    def power_into_source(self) -> HighspyArray:
        """Return effective power flowing into the source element.

        This is the t→s output from the last segment minus the s→t input to the first segment.

        """
        return self._last.power_out_ts - self._first.power_in_st

    @property
    def power_into_target(self) -> HighspyArray:
        """Return effective power flowing into the target element.

        This is the s→t output from the last segment minus the t→s input to the first segment.

        """
        return self._last.power_out_st - self._first.power_in_ts

    # --- Constraint and cost delegation to segments ---

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Return all constraints from this connection and its segments.

        Calls constraints() on each segment to collect their reactive constraints,
        then adds the connection's own constraints (segment linking).

        Returns:
            Dictionary mapping constraint method names to constraint objects

        """
        # Collect constraints from all segments
        result: dict[str, highs_cons | list[highs_cons]] = {}
        for segment in self._segments.values():
            segment_constraints = segment.constraints()
            for name, cons in segment_constraints.items():
                # Prefix with segment id to avoid collisions
                result[f"{segment.segment_id}_{name}"] = cons

        # Add our own constraints (segment linking)
        own_constraints = super().constraints()
        result.update(own_constraints)

        return result

    def cost(self) -> ObjectiveCost | None:  # type: ignore[override]  # Intentionally override Element's @cost with segment delegation
        """Return aggregated objective expressions from this connection.

        Collects costs from all segments and adds a time-preference objective to
        prefer earlier energy transfer when primary costs are equal.

        Returns:
            ObjectiveCost container or None if no objectives are defined

        """
        # Collect costs from all segments
        costs = [
            as_objective_cost(segment_cost)
            for segment in self._segments.values()
            if (segment_cost := segment.cost()) is not None
        ]

        # Add time preference objective (secondary only)
        if (time_preference := self._time_preference_objective()) is not None:
            costs.append(time_preference)

        if not costs:
            return None

        combined = combine_objectives(costs)
        return None if combined.is_empty else combined

    def _time_preference_objective(self) -> ObjectiveCost | None:
        """Return secondary objective that prefers earlier energy transfer."""
        if self.n_periods == 0:
            return None

        weights = time_preference_weights(self.periods)
        energy_st = self.power_source_target * self.periods
        energy_ts = self.power_target_source * self.periods

        secondary_terms = [
            Highs.qsum(energy_st * weights),
            Highs.qsum(energy_ts * weights),
        ]

        secondary = Highs.qsum(secondary_terms) if len(secondary_terms) > 1 else secondary_terms[0]
        return ObjectiveCost(primary=None, secondary=secondary)

    # --- Segment linking constraints ---

    @constraint
    def segment_link_st(self) -> list[highs_linear_expression] | None:
        """Link s→t power between adjacent segments."""
        if len(self._segments) < MIN_SEGMENTS_FOR_LINKING:
            return None

        constraints = []
        segment_list = list(self._segments.values())
        for i in range(len(segment_list) - 1):
            curr = segment_list[i]
            next_seg = segment_list[i + 1]
            # Output of current segment feeds input of next segment
            constraints.extend(list(curr.power_out_st == next_seg.power_in_st))
        return constraints

    @constraint
    def segment_link_ts(self) -> list[highs_linear_expression] | None:
        """Link t→s power between adjacent segments."""
        if len(self._segments) < MIN_SEGMENTS_FOR_LINKING:
            return None

        constraints = []
        segment_list = list(self._segments.values())
        for i in range(len(segment_list) - 1):
            curr = segment_list[i]
            next_seg = segment_list[i + 1]
            # Output of current segment feeds input of next segment
            constraints.extend(list(curr.power_out_ts == next_seg.power_in_ts))
        return constraints

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
    "CONNECTION_TIME_SLICE",
    "ELEMENT_TYPE",
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputName",
    "ConnectionOutputValue",
    "ConnectionSegmentOutputs",
]
