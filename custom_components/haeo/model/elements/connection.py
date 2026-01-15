"""Connection element for power flow between nodes.

Connection composes multiple segments (efficiency, power limits, pricing)
to model various connection behaviors.
"""

from collections.abc import Sequence
from typing import Any, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import constraint, output
from custom_components.haeo.model.util import broadcast_to_sequence

from .segments import EfficiencySegment, PassthroughSegment, PowerLimitSegment, PricingSegment, Segment

# Efficiency is specified as percentage (0-100), convert to fraction
EFFICIENCY_PERCENT = 100.0

# Minimum segments needed before linking is required
MIN_SEGMENTS_FOR_LINKING = 2


type ConnectionOutputName = Literal[
    "connection_power_source_target",
    "connection_power_target_source",
    "connection_shadow_power_max_source_target",
    "connection_shadow_power_max_target_source",
    "connection_time_slice",
]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_SOURCE_TARGET := "connection_power_source_target",
        CONNECTION_POWER_TARGET_SOURCE := "connection_power_target_source",
        CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET := "connection_shadow_power_max_source_target",
        CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE := "connection_shadow_power_max_target_source",
        CONNECTION_TIME_SLICE := "connection_time_slice",
    )
)


class Connection[TOutputName: str](Element[TOutputName]):
    """Connection element for power flow between nodes.

    Segments are chained in order:
    1. EfficiencySegment (if efficiency != 100%)
    2. PowerLimitSegment (if limits specified)
    3. PricingSegment (if pricing specified)

    Each segment owns its own power variables and TrackedParams. The connection
    links adjacent segments by constraining their output to the next segment's input.

    For warm-start updates, access the relevant segment directly:
    - connection.power_limit_segment.max_power_st = new_value
    - connection.pricing_segment.price_st = new_value
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        source: str,
        target: str,
        output_names: frozenset[TOutputName] | None = None,
        max_power_source_target: float | Sequence[float] | None = None,
        max_power_target_source: float | Sequence[float] | None = None,
        fixed_power: bool = False,
        efficiency_source_target: float | Sequence[float] | None = None,
        efficiency_target_source: float | Sequence[float] | None = None,
        price_source_target: float | Sequence[float] | None = None,
        price_target_source: float | Sequence[float] | None = None,
        _skip_segments: bool = False,
    ) -> None:
        """Initialize a connection.

        Args:
            name: Name of the connection
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance
            source: Name of the source element
            target: Name of the target element
            output_names: Output names for this connection type
            max_power_source_target: Maximum power flow s→t in kW
            max_power_target_source: Maximum power flow t→s in kW
            fixed_power: If True, power flow is fixed to max_power values
            efficiency_source_target: Efficiency % for s→t flow (0-100)
            efficiency_target_source: Efficiency % for t→s flow (0-100)
            price_source_target: Price $/kWh for s→t flow
            price_target_source: Price $/kWh for t→s flow
            _skip_segments: If True, skip segment creation (for subclasses with custom power flow)

        """
        # Use provided output_names or default to CONNECTION_OUTPUT_NAMES
        actual_output_names: frozenset[Any] = (
            output_names if output_names is not None else CONNECTION_OUTPUT_NAMES
        )
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
        self._fixed_power = fixed_power

        # Initialize segment-related attributes (may be empty if subclass handles power flow)
        self._segments: list[Segment] = []
        self._power_limit_segment: PowerLimitSegment | None = None
        self._pricing_segment: PricingSegment | None = None
        self._first: Segment | None = None
        self._last: Segment | None = None

        # Skip segment creation for subclasses that handle power flow themselves
        if _skip_segments:
            return

        # Broadcast scalars to arrays
        max_power_st = broadcast_to_sequence(max_power_source_target, n_periods)
        max_power_ts = broadcast_to_sequence(max_power_target_source, n_periods)
        price_st = broadcast_to_sequence(price_source_target, n_periods)
        price_ts = broadcast_to_sequence(price_target_source, n_periods)

        # Build segment chain
        segment_idx = 0

        # Efficiency segment (if non-default efficiency)
        eff_st = broadcast_to_sequence(efficiency_source_target, n_periods)
        eff_ts = broadcast_to_sequence(efficiency_target_source, n_periods)
        needs_efficiency = (eff_st is not None and np.any(eff_st != EFFICIENCY_PERCENT)) or (
            eff_ts is not None and np.any(eff_ts != EFFICIENCY_PERCENT)
        )

        if needs_efficiency:
            eff_segment = EfficiencySegment(
                f"{name}_seg_{segment_idx}",
                n_periods,
                periods_array,
                solver,
                efficiency_st=eff_st / EFFICIENCY_PERCENT if eff_st is not None else None,
                efficiency_ts=eff_ts / EFFICIENCY_PERCENT if eff_ts is not None else None,
            )
            self._segments.append(eff_segment)
            segment_idx += 1

        # Power limit segment (if limits specified)
        if max_power_st is not None or max_power_ts is not None:
            self._power_limit_segment = PowerLimitSegment(
                f"{name}_seg_{segment_idx}",
                n_periods,
                periods_array,
                solver,
                max_power_st=max_power_st,
                max_power_ts=max_power_ts,
                fixed=fixed_power,
            )
            self._segments.append(self._power_limit_segment)
            segment_idx += 1

        # Pricing segment (if prices specified)
        if price_st is not None or price_ts is not None:
            self._pricing_segment = PricingSegment(
                f"{name}_seg_{segment_idx}",
                n_periods,
                periods_array,
                solver,
                price_st=price_st,
                price_ts=price_ts,
            )
            self._segments.append(self._pricing_segment)
            segment_idx += 1

        # If no segments needed, create a passthrough segment (just power variables)
        if not self._segments:
            passthrough = PassthroughSegment(f"{name}_seg_0", n_periods, periods_array, solver)
            self._segments.append(passthrough)

        # Store edge references (first and last segment power variables)
        self._first = self._segments[0]
        self._last = self._segments[-1]

    # Parameter names that are delegated to segments
    _DELEGATED_PARAMS: frozenset[str] = frozenset(
        {
            "max_power_source_target",
            "max_power_target_source",
            "price_source_target",
            "price_target_source",
        }
    )

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a TrackedParam value by name.

        Handles both Element-level TrackedParams and parameters delegated to segments.

        Args:
            key: Name of the parameter
            value: New value to set

        Raises:
            KeyError: If no TrackedParam or delegated property with this name exists

        """
        if key in self._DELEGATED_PARAMS:
            # Use property setter for delegated params
            setattr(self, key, value)
            return

        # Fall back to Element's TrackedParam handling
        super().__setitem__(key, value)

    @property
    def power_limit_segment(self) -> PowerLimitSegment | None:
        """Return the power limit segment, or None if not present."""
        return self._power_limit_segment

    @property
    def pricing_segment(self) -> PricingSegment | None:
        """Return the pricing segment, or None if not present."""
        return self._pricing_segment

    # --- Convenience properties for accessing/updating segment parameters ---
    # These delegate to the appropriate segment, enabling warm-start updates
    # without requiring knowledge of the segment structure.

    @property
    def max_power_source_target(self) -> NDArray[np.float64] | None:
        """Return max power for source→target direction, or None if no limit."""
        return self._power_limit_segment.max_power_st if self._power_limit_segment else None

    @max_power_source_target.setter
    def max_power_source_target(self, value: NDArray[np.float64] | None) -> None:
        """Set max power for source→target direction (for warm-start updates)."""
        if self._power_limit_segment is None:
            msg = "Cannot set max_power_source_target: no power limit segment"
            raise KeyError(msg)
        self._power_limit_segment.max_power_st = value

    @property
    def max_power_target_source(self) -> NDArray[np.float64] | None:
        """Return max power for target→source direction, or None if no limit."""
        return self._power_limit_segment.max_power_ts if self._power_limit_segment else None

    @max_power_target_source.setter
    def max_power_target_source(self, value: NDArray[np.float64] | None) -> None:
        """Set max power for target→source direction (for warm-start updates)."""
        if self._power_limit_segment is None:
            msg = "Cannot set max_power_target_source: no power limit segment"
            raise KeyError(msg)
        self._power_limit_segment.max_power_ts = value

    @property
    def price_source_target(self) -> NDArray[np.float64] | None:
        """Return price for source→target direction, or None if no pricing."""
        return self._pricing_segment.price_st if self._pricing_segment else None

    @price_source_target.setter
    def price_source_target(self, value: NDArray[np.float64] | None) -> None:
        """Set price for source→target direction (for warm-start updates)."""
        if self._pricing_segment is None:
            msg = "Cannot set price_source_target: no pricing segment"
            raise KeyError(msg)
        self._pricing_segment.price_st = value

    @property
    def price_target_source(self) -> NDArray[np.float64] | None:
        """Return price for target→source direction, or None if no pricing."""
        return self._pricing_segment.price_ts if self._pricing_segment else None

    @price_target_source.setter
    def price_target_source(self, value: NDArray[np.float64] | None) -> None:
        """Set price for target→source direction (for warm-start updates)."""
        if self._pricing_segment is None:
            msg = "Cannot set price_target_source: no pricing segment"
            raise KeyError(msg)
        self._pricing_segment.price_ts = value

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
        for segment in self._segments:
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
        costs = [segment_cost for segment in self._segments if (segment_cost := segment.cost()) is not None]

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
        for i in range(len(self._segments) - 1):
            curr = self._segments[i]
            next_seg = self._segments[i + 1]
            # Output of current segment feeds input of next segment
            constraints.extend(list(curr.power_out_st == next_seg.power_in_st))
        return constraints

    @constraint
    def segment_link_ts(self) -> list[highs_linear_expression] | None:
        """Link t→s power between adjacent segments."""
        if len(self._segments) < MIN_SEGMENTS_FOR_LINKING:
            return None

        constraints = []
        for i in range(len(self._segments) - 1):
            curr = self._segments[i]
            next_seg = self._segments[i + 1]
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

    @output
    def connection_shadow_power_max_source_target(self) -> OutputData | None:
        """Shadow price for source→target power limit constraint."""
        if self._power_limit_segment is None:
            return None

        # Get constraint from segment's reactive state
        state_attr = "_reactive_state_power_limit_st"
        state = getattr(self._power_limit_segment, state_attr, None)
        if state is None or "constraint" not in state:
            return None

        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit="$/kW",
            values=self.extract_values(state["constraint"]),
        )

    @output
    def connection_shadow_power_max_target_source(self) -> OutputData | None:
        """Shadow price for target→source power limit constraint."""
        if self._power_limit_segment is None:
            return None

        # Get constraint from segment's reactive state
        state_attr = "_reactive_state_power_limit_ts"
        state = getattr(self._power_limit_segment, state_attr, None)
        if state is None or "constraint" not in state:
            return None

        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit="$/kW",
            values=self.extract_values(state["constraint"]),
        )

    @output
    def connection_time_slice(self) -> OutputData | None:
        """Shadow price for time-slice constraint."""
        if self._power_limit_segment is None:
            return None

        # Get constraint from segment's reactive state
        state_attr = "_reactive_state_time_slice"
        state = getattr(self._power_limit_segment, state_attr, None)
        if state is None or "constraint" not in state:
            return None

        return OutputData(
            type=OutputType.SHADOW_PRICE,
            unit="$/kW",
            values=self.extract_values(state["constraint"]),
        )


__all__ = [
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET",
    "CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
    "Connection",
    "ConnectionOutputName",
]
