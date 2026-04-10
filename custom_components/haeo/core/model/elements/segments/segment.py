"""Base class for connection segments.

Segments are modular components that can be chained together to form
connections. Each segment exposes power flow properties that the Connection
uses to link segments together.

The linking protocol:
- power_in_st / power_in_ts: Power entering this segment
- power_out_st / power_out_ts: Power leaving this segment

For simple segments (no losses), in == out (same variable).
For segments with losses (efficiency), out = in * factor (separate variables with constraint).

Tagged power:
- When tags are configured, the segment creates per-tag power variables
  that decompose the total power flow.
- Constraint: sum(tagged_power[tag]) == total_power for each period/direction
- Existing constraints operate on total power (unchanged).
- Tag-specific constraints are additive (via TagPricingSegment, TagFilterSegment).
- Per-tag linking between adjacent segments is handled by Connection.

Segments are reactive-aware: they can use TrackedParam for parameters and
@constraint/@cost decorators for methods.
"""

from abc import ABC, abstractmethod
from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import OutputMethod, ReactiveConstraint, ReactiveCost, TrackedParam


class Segment(ABC):
    """Abstract base class for connection segments.

    Defines the interface that all segments must implement. Subclasses create
    their own variables and implement the power properties as needed.

    Required properties (subclasses must implement):
    - power_in_st / power_out_st: Power flow in source→target direction
    - power_in_ts / power_out_ts: Power flow in target→source direction

    For simple segments, power_in and power_out can return the same variable.
    For segments with losses, power_out = power_in * efficiency (via constraint).

    Tagged power:
    When tags are provided, the segment creates per-tag variables that decompose
    the total power flow. Access via tagged_power_in_st(tag), etc.
    A constraint ensures sum(tagged) == total for each period and direction.
    """

    # TrackedParam for periods - enables reactive invalidation when periods change
    periods: TrackedParam[NDArray[np.floating[Any]]] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        source_element: Element[Any],
        target_element: Element[Any],
        tags: list[str] | None = None,
    ) -> None:
        """Initialize segment with common attributes.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            source_element: Connected source element reference
            target_element: Connected target element reference
            tags: Optional list of tag names for tagged power decomposition

        """
        self._segment_id = segment_id
        self._n_periods = n_periods
        self.periods = np.asarray(periods, dtype=float)
        self._solver = solver
        self._source_element = source_element
        self._target_element = target_element

        # Tagged power variables: tag -> {"st": HighspyArray, "ts": HighspyArray}
        self._tags: list[str] = list(tags) if tags else []
        self._tagged_power: dict[str, dict[str, HighspyArray]] = {}
        # Decomposition constraints stored for solver management
        self._tag_decomposition_constraints: list[highs_cons] = []

    @property
    def segment_id(self) -> str:
        """Return the segment identifier."""
        return self._segment_id

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return self._n_periods

    @property
    def source_element(self) -> Element[Any]:
        """Return the source element reference."""
        return self._source_element

    @property
    def target_element(self) -> Element[Any]:
        """Return the target element reference."""
        return self._target_element

    @property
    def tags(self) -> list[str]:
        """Return the list of configured tags."""
        return self._tags

    @property
    def has_tags(self) -> bool:
        """Return True when tagged power decomposition is active."""
        return len(self._tags) > 0

    def initialize_tags(self) -> None:
        """Create per-tag power variables and decomposition constraints.

        Must be called AFTER the subclass constructor has created the total
        power variables (power_in_st, power_in_ts, etc.).
        This is called by the Connection after segment creation.
        """
        if not self._tags or self._tagged_power:
            return  # No tags or already initialized

        for tag in self._tags:
            st_vars = self._solver.addVariables(
                self._n_periods, lb=0,
                name_prefix=f"{self._segment_id}_tag_{tag}_st_",
                out_array=True,
            )
            ts_vars = self._solver.addVariables(
                self._n_periods, lb=0,
                name_prefix=f"{self._segment_id}_tag_{tag}_ts_",
                out_array=True,
            )
            self._tagged_power[tag] = {"st": st_vars, "ts": ts_vars}

        # Decomposition constraint: sum of tagged == total for each period/direction
        tag_sum_st = sum(self._tagged_power[tag]["st"] for tag in self._tags)
        tag_sum_ts = sum(self._tagged_power[tag]["ts"] for tag in self._tags)

        # Constrain tag sum == total power input
        self._tag_decomposition_constraints.extend(
            self._solver.addConstrs(tag_sum_st == self.power_in_st)
        )
        self._tag_decomposition_constraints.extend(
            self._solver.addConstrs(tag_sum_ts == self.power_in_ts)
        )

    def tagged_power_in_st(self, tag: str) -> HighspyArray:
        """Return per-tag power entering segment in source→target direction.

        Raises KeyError if the tag is not configured.
        """
        return self._tagged_power[tag]["st"]

    def tagged_power_in_ts(self, tag: str) -> HighspyArray:
        """Return per-tag power entering segment in target→source direction.

        Raises KeyError if the tag is not configured.
        """
        return self._tagged_power[tag]["ts"]

    def tagged_power_out_st(self, tag: str) -> HighspyArray:
        """Return per-tag power leaving segment in source→target direction.

        For lossless segments (in == out), returns the same as tagged_power_in_st.
        For efficiency segments, subclasses should override to apply efficiency.
        """
        # Default: lossless (in == out). Subclasses with losses override.
        return self.tagged_power_in_st(tag)

    def tagged_power_out_ts(self, tag: str) -> HighspyArray:
        """Return per-tag power leaving segment in target→source direction.

        For lossless segments (in == out), returns the same as tagged_power_in_ts.
        For efficiency segments, subclasses should override to apply efficiency.
        """
        # Default: lossless (in == out). Subclasses with losses override.
        return self.tagged_power_in_ts(tag)

    @property
    @abstractmethod
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        ...

    @property
    @abstractmethod
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction."""
        ...

    @property
    @abstractmethod
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        ...

    @property
    @abstractmethod
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction."""
        ...

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Return all constraints from this segment.

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

    def outputs(self) -> dict[str, OutputData]:
        """Return output data from output and constraint methods."""
        result: dict[str, OutputData] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, OutputMethod):
                output_name = attr.output_name
            elif isinstance(attr, ReactiveConstraint):
                output_name = name
            else:
                continue

            output_data = attr.get_output(self)
            if isinstance(output_data, OutputData):
                result[output_name] = output_data
        return result

    def cost(self) -> Any:
        """Return aggregated cost expression from this segment.

        Discovers and calls all @cost decorated methods, summing their results.

        Returns:
            Cost expression or None if no costs

        """
        costs: list[Any] = []
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if not isinstance(attr, ReactiveCost):
                continue

            # Call the cost method
            method = getattr(self, name)
            if (cost_value := method()) is not None:
                if isinstance(cost_value, list):
                    costs.extend(cost_value)
                else:
                    costs.append(cost_value)

        if not costs:
            return None
        if len(costs) == 1:
            return costs[0]
        return sum(costs[1:], costs[0])


__all__ = ["Segment"]
