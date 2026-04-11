"""Base class for connection segments.

Segments are modular components that can be chained together to form
connections. Each segment exposes power flow properties that the Connection
uses to link segments together.

Power flow model:
- All power is tagged. Every connection has at least tag 0 (untagged/default).
- Each segment creates per-tag LP variables for each direction.
- power_in_st / power_out_st return the sum across all tags (total power).
- Segments can be scoped to a specific tag via the `tag` spec parameter.
  Scoped segments' constraints/costs apply only to that tag's variables.
  Their power_in/out properties return that tag's variables, not the sum.

The linking protocol:
- power_in_st / power_in_ts: Power entering this segment (sum or tag-scoped)
- power_out_st / power_out_ts: Power leaving this segment (sum or tag-scoped)
- Per-tag linking between adjacent segments is handled by Connection.

For simple segments (no losses), in == out per tag (same variable).
For segments with losses (efficiency), out = in * factor per tag.

Segments are reactive-aware: they can use TrackedParam for parameters and
@constraint/@cost decorators for methods.
"""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import OutputMethod, ReactiveConstraint, ReactiveCost, TrackedParam

# Default tag for untagged power (like VLAN 0)
DEFAULT_TAG: int = 0


class Segment:
    """Abstract base class for connection segments.

    All power flow is decomposed into tags. Each segment creates LP variables
    per tag per direction. The "total" power is the sum across all tags.

    Segments can be scoped to a specific tag. When scoped:
    - power_in_st/ts return that tag's variables (not the sum)
    - constraints and costs apply to that tag only

    When unscoped (tag=None):
    - power_in_st/ts return the sum across all tags
    - constraints and costs apply to the total

    Subclasses implement _create_tag_variables() to define how per-tag
    variables relate (lossless: in == out, or efficiency: out = in * eff).
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
    ) -> None:
        """Initialize segment with common attributes.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            source_element: Connected source element reference
            target_element: Connected target element reference

        """
        self._segment_id = segment_id
        self._n_periods = n_periods
        self.periods = np.asarray(periods, dtype=float)
        self._solver = solver
        self._source_element = source_element
        self._target_element = target_element

        # Per-tag power variables: tag_id -> {"in_st", "out_st", "in_ts", "out_ts"}
        self._tag_power: dict[int, dict[str, HighspyArray]] = {}
        # The list of tags this segment knows about
        self._tags: list[int] = []
        # Optional: scope this segment to a specific tag or set of tags
        # None = apply to total (sum of all tags)
        # int = apply to a single tag
        # set[int] = apply to the sum of the specified tags
        self._scoped_tag: int | None = None
        self._scoped_tags: frozenset[int] | None = None

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
    def tags(self) -> list[int]:
        """Return the list of tag IDs for this segment."""
        return self._tags

    @property
    def scoped_tag(self) -> int | None:
        """Return the tag this segment is scoped to, or None for all."""
        return self._scoped_tag

    def initialize_tags(self, tags: list[int]) -> None:
        """Create per-tag power variables.

        Called by the Connection after segment creation. Creates LP variables
        for each tag. Subclasses control the in/out relationship via
        _create_tag_variables().

        Args:
            tags: List of tag IDs (always includes DEFAULT_TAG).

        """
        if self._tag_power:
            return  # Already initialized
        self._tags = list(tags)
        for tag in tags:
            self._tag_power[tag] = self._create_tag_variables(tag)

    def _create_tag_variables(self, tag: int) -> dict[str, HighspyArray]:
        """Create LP variables for a single tag.

        Default implementation: lossless (in == out, same variable).
        Subclasses override for losses (e.g., efficiency creates separate in/out).

        Returns:
            Dict with keys "in_st", "out_st", "in_ts", "out_ts" -> HighspyArray.

        """
        st = self._solver.addVariables(
            self._n_periods,
            lb=0,
            name_prefix=f"{self._segment_id}_t{tag}_st_",
            out_array=True,
        )
        ts = self._solver.addVariables(
            self._n_periods,
            lb=0,
            name_prefix=f"{self._segment_id}_t{tag}_ts_",
            out_array=True,
        )
        return {"in_st": st, "out_st": st, "in_ts": ts, "out_ts": ts}

    # --- Per-tag access ---

    def tag_power_in_st(self, tag: int) -> HighspyArray:
        """Return power entering segment in s→t direction for a specific tag."""
        return self._tag_power[tag]["in_st"]

    def tag_power_out_st(self, tag: int) -> HighspyArray:
        """Return power leaving segment in s→t direction for a specific tag."""
        return self._tag_power[tag]["out_st"]

    def tag_power_in_ts(self, tag: int) -> HighspyArray:
        """Return power entering segment in t→s direction for a specific tag."""
        return self._tag_power[tag]["in_ts"]

    def tag_power_out_ts(self, tag: int) -> HighspyArray:
        """Return power leaving segment in t→s direction for a specific tag."""
        return self._tag_power[tag]["out_ts"]

    # --- Aggregate / scoped access (used by constraints and linking) ---

    def _sum_across_tags(self, key: str) -> HighspyArray:
        """Sum a specific power key across all tags."""
        arrays = [self._tag_power[tag][key] for tag in self._tags]
        if len(arrays) == 1:
            return arrays[0]
        result = arrays[0]
        for arr in arrays[1:]:
            result = result + arr
        return result

    def _get_scoped_power(self, key: str) -> HighspyArray:
        """Return power for the configured scope.

        - _scoped_tag set: returns that single tag's variable
        - _scoped_tags set: returns sum of those tags' variables
        - neither set: returns sum across ALL tags (total)
        """
        if self._scoped_tag is not None:
            return self._tag_power[self._scoped_tag][key]
        if self._scoped_tags is not None:
            arrays = [self._tag_power[tag][key] for tag in self._scoped_tags if tag in self._tag_power]
            if not arrays:
                return self._sum_across_tags(key)
            if len(arrays) == 1:
                return arrays[0]
            result = arrays[0]
            for arr in arrays[1:]:
                result = result + arr
            return result
        return self._sum_across_tags(key)

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        self._ensure_tags_initialized()
        return self._get_scoped_power("in_st")

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction."""
        self._ensure_tags_initialized()
        return self._get_scoped_power("out_st")

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        self._ensure_tags_initialized()
        return self._get_scoped_power("in_ts")

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction."""
        self._ensure_tags_initialized()
        return self._get_scoped_power("out_ts")

    def _ensure_tags_initialized(self) -> None:
        """Auto-initialize with DEFAULT_TAG if no tags have been set."""
        if not self._tag_power:
            self.initialize_tags([DEFAULT_TAG])

    def total_power_in_st(self) -> HighspyArray:
        """Total power entering segment in s→t (sum across all tags, ignoring scope)."""
        self._ensure_tags_initialized()
        return self._sum_across_tags("in_st")

    def total_power_out_st(self) -> HighspyArray:
        """Total power leaving segment in s→t (sum across all tags, ignoring scope)."""
        self._ensure_tags_initialized()
        return self._sum_across_tags("out_st")

    def total_power_in_ts(self) -> HighspyArray:
        """Total power entering segment in t→s (sum across all tags, ignoring scope)."""
        self._ensure_tags_initialized()
        return self._sum_across_tags("in_ts")

    def total_power_out_ts(self) -> HighspyArray:
        """Total power leaving segment in t→s (sum across all tags, ignoring scope)."""
        self._ensure_tags_initialized()
        return self._sum_across_tags("out_ts")

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


__all__ = ["DEFAULT_TAG", "Segment"]
