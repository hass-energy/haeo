"""Efficiency segment that applies losses to power flow.

Efficiency reduces output power relative to input:
    power_out = power_in * efficiency

This models inverter losses, transformer losses, etc.
"""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.reactive import TrackedParam
from custom_components.haeo.model.util import broadcast_to_sequence

from .segment import Segment


class EfficiencySegmentSpec(TypedDict):
    """Specification for creating an EfficiencySegment."""

    segment_type: Literal["efficiency"]
    efficiency_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    efficiency_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class EfficiencySegment(Segment):
    """Segment that applies efficiency losses to power flow.

    Uses a single variable per direction with efficiency applied via properties:
        power_out_st = power_in_st * efficiency_source_target
        power_out_ts = power_in_ts * efficiency_target_source

    Efficiency values are fractions in range (0, 1].
    """

    efficiency_source_target: TrackedParam[NDArray[np.float64]] = TrackedParam()
    efficiency_target_source: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: EfficiencySegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
    ) -> None:
        """Initialize efficiency segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            spec: Efficiency segment specification.
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

        # Store efficiency values
        efficiency_source_target = spec.get("efficiency_source_target")
        self.efficiency_source_target = broadcast_to_sequence(
            1.0 if efficiency_source_target is None else efficiency_source_target, self._n_periods
        )
        efficiency_target_source = spec.get("efficiency_target_source")
        self.efficiency_target_source = broadcast_to_sequence(
            1.0 if efficiency_target_source is None else efficiency_target_source, self._n_periods
        )

        # Single variable per direction - efficiency applied via properties
        self._power_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_st_", out_array=True)
        self._power_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_ts_", out_array=True)

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_st

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction (after efficiency loss)."""
        return self._power_st * self.efficiency_source_target

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_ts

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction (after efficiency loss)."""
        return self._power_ts * self.efficiency_target_source


__all__ = ["EfficiencySegment", "EfficiencySegmentSpec"]
