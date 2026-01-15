"""Connection element for power flow between nodes.

Connection composes multiple segments (efficiency, power limits, pricing)
to model various connection behaviors.
"""

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any, Final, Literal, NotRequired, TypedDict, cast

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import ReactiveConstraint, constraint, output

from .segments import SEGMENT_TYPES, PassthroughSegment, Segment, SegmentSpec

# Model element type for connections
ELEMENT_TYPE: Final = "connection"
type ConnectionElementTypeName = Literal["connection"]


class ConnectionElementConfig(TypedDict):
    """Configuration for Connection model elements."""

    element_type: ConnectionElementTypeName
    name: str
    source: str
    target: str
    segments: NotRequired[Sequence[SegmentSpec]]

# Minimum segments needed before linking is required
MIN_SEGMENTS_FOR_LINKING = 2


type ConnectionOutputName = Literal[
    "connection_power_source_target",
    "connection_power_target_source",
    "connection_shadow_power_max_source_target",
    "connection_shadow_power_max_target_source",
    "connection_time_slice",
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
    )
)


class Connection[TOutputName: str](Element[TOutputName]):
    """Connection element for power flow between nodes.

    Segments are provided as a list of segment specifications, each containing:
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
        periods: Sequence[float],
        *,
        solver: Highs,
        source: str,
        target: str,
        segments: Sequence[SegmentSpec] | None = None,
        output_names: frozenset[TOutputName] | None = None,
        _skip_segments: bool = False,
    ) -> None:
        """Initialize a connection.

        Args:
            name: Name of the connection
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance
            source: Name of the source element
            target: Name of the target element
            segments: List of segment specifications (SegmentSpec TypedDicts).
                Each spec has segment_type plus segment-specific parameters.
            output_names: Output names for this connection type
            _skip_segments: If True, skip segment creation (for subclasses with custom power flow)

        """
        # Use provided output_names or default to CONNECTION_OUTPUT_NAMES
        actual_output_names: frozenset[Any] = output_names if output_names is not None else CONNECTION_OUTPUT_NAMES
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=actual_output_names,
        )
        n_periods = self.n_periods
        periods_array = np.asarray(periods)

        self._source = source
        self._target = target

        # Segments stored in OrderedDict for name-based and index-based access
        self._segments: OrderedDict[str, Segment] = OrderedDict()

        # Skip segment creation for subclasses that handle power flow themselves
        if _skip_segments:
            return

        segment_specs = list(segments) if segments else []

        for idx, segment_spec in enumerate(segment_specs):
            # Extract segment_type (required in all specs)
            segment_type = segment_spec["segment_type"]
            segment_name = segment_spec.get("name", segment_type)

            # Ensure unique segment names
            if segment_name in self._segments:
                segment_name = f"{segment_name}_{idx}"

            # Get segment class from registry
            segment_cls = SEGMENT_TYPES[segment_type]

            # Build kwargs from spec, excluding segment_type and name
            seg_kwargs: dict[str, Any] = {k: v for k, v in segment_spec.items() if k not in ("segment_type", "name")}

            # Create segment with standard args plus kwargs from spec
            segment_id = f"{name}_{segment_name}"
            segment = segment_cls(
                segment_id,
                n_periods,
                periods_array,
                solver,
                **seg_kwargs,
            )
            self._segments[segment_name] = segment

        # If no segments provided, create a passthrough segment
        if not self._segments:
            passthrough = PassthroughSegment(f"{name}_passthrough", n_periods, periods_array, solver)
            self._segments["passthrough"] = passthrough

    @property
    def segments(self) -> OrderedDict[str, Segment]:
        """Return the ordered dict of segments."""
        return self._segments

    def __getitem__(self, key: str | int) -> Segment:
        """Access a segment by name or index."""
        if isinstance(key, int):
            return list(self._segments.values())[key]

        if key in self._segments:
            return self._segments[key]

        msg = f"{type(self).__name__!r} has no segment {key!r}"
        raise KeyError(msg)

    def __setitem__(self, key: str | int, value: Any) -> None:
        """Set a TrackedParam value for connection subclasses."""
        if isinstance(key, int):
            msg = "Cannot assign segments via index"
            raise KeyError(msg)

        if key in self._segments:
            msg = "Cannot replace segments via assignment"
            raise KeyError(msg)

        super().__setitem__(key, value)

    @property
    def _first(self) -> Segment | None:
        """Return the first segment in the chain."""
        if not self._segments:
            return None
        return next(iter(self._segments.values()))

    @property
    def _last(self) -> Segment | None:
        """Return the last segment in the chain."""
        if not self._segments:
            return None
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
        """Return power flowing from source to target (input to first segment).

        Note: Subclasses using _skip_segments=True must override this property.
        """
        if self._first is None:
            msg = f"{type(self).__name__} must override power_source_target when using _skip_segments=True"
            raise NotImplementedError(msg)
        return self._first.power_in_st

    @property
    def power_target_source(self) -> HighspyArray:
        """Return power flowing from target to source (input to first segment from t→s direction).

        Note: Subclasses using _skip_segments=True must override this property.
        """
        if self._first is None:
            msg = f"{type(self).__name__} must override power_target_source when using _skip_segments=True"
            raise NotImplementedError(msg)
        return self._first.power_in_ts

    @property
    def power_into_source(self) -> HighspyArray:
        """Return effective power flowing into the source element.

        This is the t→s output from the last segment minus the s→t input to the first segment.

        Note: Subclasses using _skip_segments=True must override this property.
        """
        if self._last is None or self._first is None:
            msg = f"{type(self).__name__} must override power_into_source when using _skip_segments=True"
            raise NotImplementedError(msg)
        return self._last.power_out_ts - self._first.power_in_st

    @property
    def power_into_target(self) -> HighspyArray:
        """Return effective power flowing into the target element.

        This is the s→t output from the last segment minus the t→s input to the first segment.

        Note: Subclasses using _skip_segments=True must override this property.
        """
        if self._last is None or self._first is None:
            msg = f"{type(self).__name__} must override power_into_target when using _skip_segments=True"
            raise NotImplementedError(msg)
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

    def cost(self) -> Any:  # type: ignore[override]  # Intentionally override Element's @cost with segment delegation
        """Return aggregated cost expression from this connection's segments.

        Collects costs from all segments and aggregates them.

        Note: Subclasses with @cost methods (like BatteryBalanceConnection) should
        override this method to include their own costs.

        Returns:
            Aggregated cost expression or None if no costs

        """
        # Collect costs from all segments
        costs = [segment_cost for segment in self._segments.values() if (segment_cost := segment.cost()) is not None]

        if not costs:
            return None
        if len(costs) == 1:
            return costs[0]
        return Highs.qsum(costs)

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

    def outputs(self) -> Mapping[str, ConnectionOutputValue]:  # type: ignore[override]
        """Return output specifications including segment outputs.

        Collects:
        1. Connection's own @output decorated methods (power flows)
        2. Shadow prices from segment @constraint(output=True) methods

        Segment outputs are grouped under the `segments` key to avoid name collisions.
        """
        # Get connection's own outputs (power_source_target, power_target_source)
        result: dict[str, ConnectionOutputValue] = cast(
            "dict[str, ConnectionOutputValue]", dict(super().outputs())
        )
        segment_outputs: ConnectionSegmentOutputs = {}

        # Aggregate outputs from all segments
        for segment_name, segment in self._segments.items():
            # Find constraint methods with output=True on this segment
            for name in dir(type(segment)):
                attr = getattr(type(segment), name, None)
                if not isinstance(attr, ReactiveConstraint):
                    continue
                if not attr.output:
                    continue

                # Get the constraint state
                state_attr = f"_reactive_state_{name}"
                state = getattr(segment, state_attr, None)
                if state is None or "constraint" not in state:
                    continue

                # Create output with the constraint name
                output_data = OutputData(
                    type=OutputType.SHADOW_PRICE,
                    unit=attr.unit or "$/kW",
                    values=self.extract_values(state["constraint"]),
                )
                segment_outputs.setdefault(segment_name, {})[name] = output_data

                # Backward-compatible aliases for legacy connection shadow price names
                if segment_name == "power_limit":
                    if name == "source_target":
                        result[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = output_data
                    if name == "target_source":
                        result[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = output_data
                    if name == "time_slice":
                        result[CONNECTION_TIME_SLICE] = output_data

        if segment_outputs:
            result[CONNECTION_SEGMENTS] = segment_outputs

        return result


__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET",
    "CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE",
    "CONNECTION_SEGMENTS",
    "CONNECTION_TIME_SLICE",
    "ELEMENT_TYPE",
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputValue",
    "ConnectionOutputName",
    "ConnectionSegmentOutputs",
]
