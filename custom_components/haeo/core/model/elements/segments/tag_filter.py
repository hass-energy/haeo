"""Tag filter segment that constrains power flow for a specific tag.

Limits or blocks power flow for a named tag:
    power_st <= max_power_source_target (for the specific tag)
    power_ts <= max_power_target_source (for the specific tag)

Set max_power to 0 to block flow for a tag entirely.
"""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, constraint
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment


class TagFilterSegmentSpec(TypedDict):
    """Specification for creating a TagFilterSegment."""

    segment_type: Literal["tag_filter"]
    tag: str
    max_power_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    max_power_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class TagFilterSegment(Segment):
    """Segment that limits power flow for a specific tag.

    Creates single power variables for each direction (no losses, so in == out).

    Constraints:
        power_st <= max_power_source_target
        power_ts <= max_power_target_source

    The tag field identifies which category of power flow this filter applies to.
    Set max_power to 0 to completely block a tagged power flow.

    Uses TrackedParam for max_power values to enable warm-start optimization.
    """

    # TrackedParams for warm-start support
    max_power_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    max_power_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: TagFilterSegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        """Initialize tag filter segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            spec: Tag filter segment specification.
            source_element: Connected source element reference
            target_element: Connected target element reference

        """
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
        )
        self._tag = spec["tag"]

        # Create single power variable per direction (lossless segment, in == out)
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

        # Set tracked params (these trigger reactive infrastructure)
        self.max_power_source_target = broadcast_to_sequence(spec.get("max_power_source_target"), self._n_periods)
        self.max_power_target_source = broadcast_to_sequence(spec.get("max_power_target_source"), self._n_periods)

    @property
    def tag(self) -> str:
        """Return the tag name for this filter segment."""
        return self._tag

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_st

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction (same as in, lossless)."""
        return self._power_st

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_ts

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction (same as in, lossless)."""
        return self._power_ts

    @constraint(output=True, unit="$/kW")
    def source_target(self) -> list[highs_linear_expression] | None:
        """Power limit constraint for source→target direction."""
        if self.max_power_source_target is None:
            return None
        return list(self._power_st <= self.max_power_source_target)

    @constraint(output=True, unit="$/kW")
    def target_source(self) -> list[highs_linear_expression] | None:
        """Power limit constraint for target→source direction."""
        if self.max_power_target_source is None:
            return None
        return list(self._power_ts <= self.max_power_target_source)


__all__ = ["TagFilterSegment", "TagFilterSegmentSpec"]
