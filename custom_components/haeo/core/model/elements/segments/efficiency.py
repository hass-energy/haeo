"""Efficiency segment that applies losses to power flow.

Efficiency reduces output power relative to input:
    power_out = power_in * efficiency

This models inverter losses, transformer losses, etc.
Efficiency is applied per-tag: each tag's output = input * efficiency.
"""

from typing import Any, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import Segment


class EfficiencySegmentSpec(TypedDict):
    """Specification for creating an EfficiencySegment."""

    segment_type: Literal["efficiency"]
    efficiency_source_target: NotRequired[NDArray[np.floating[Any]] | float | None]
    efficiency_target_source: NotRequired[NDArray[np.floating[Any]] | float | None]


class EfficiencySegment(Segment):
    """Segment that applies efficiency losses to power flow.

    Uses per-tag variables with efficiency applied:
        power_out_st[tag] = power_in_st[tag] * efficiency_source_target
        power_out_ts[tag] = power_in_ts[tag] * efficiency_target_source

    Efficiency values are fractions in range (0, 1].
    None means no losses (100% efficiency).
    """

    efficiency_source_target: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    efficiency_target_source: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

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
        """Initialize efficiency segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
        )

        # Store efficiency values
        self.efficiency_source_target = broadcast_to_sequence(spec.get("efficiency_source_target"), self._n_periods)
        self.efficiency_target_source = broadcast_to_sequence(spec.get("efficiency_target_source"), self._n_periods)

    @property
    def is_lossless(self) -> bool:
        """Efficiency transforms power — breaks the variable sharing chain.

        Efficiency shares the previous segment's input variables, but the
        segment after efficiency needs new variables because the output
        is an expression (input * efficiency), not the same variable.
        """
        return False

    def tag_power_out_st(self, tag: int) -> HighspyArray:
        """Per-tag output in s→t with efficiency applied."""
        efficiency = self.efficiency_source_target
        if efficiency is None:
            return self._tag_power[tag]["in_st"]
        return self._tag_power[tag]["in_st"] * efficiency

    def tag_power_out_ts(self, tag: int) -> HighspyArray:
        """Per-tag output in t→s with efficiency applied."""
        efficiency = self.efficiency_target_source
        if efficiency is None:
            return self._tag_power[tag]["in_ts"]
        return self._tag_power[tag]["in_ts"] * efficiency

    @property
    def power_out_st(self) -> HighspyArray:
        """Total power leaving segment in s→t (with efficiency, respecting scope)."""
        self._ensure_tags_initialized()
        if self._scoped_tag is not None:
            return self.tag_power_out_st(self._scoped_tag)
        if self._scoped_tags is not None:
            arrays = [self.tag_power_out_st(tag) for tag in self._scoped_tags if tag in self._tag_power]
            if not arrays:
                return self.total_power_out_st()
            if len(arrays) == 1:
                return arrays[0]
            result = arrays[0]
            for arr in arrays[1:]:
                result = result + arr
            return result
        return self.total_power_out_st()

    @property
    def power_out_ts(self) -> HighspyArray:
        """Total power leaving segment in t→s (with efficiency, respecting scope)."""
        self._ensure_tags_initialized()
        if self._scoped_tag is not None:
            return self.tag_power_out_ts(self._scoped_tag)
        if self._scoped_tags is not None:
            arrays = [self.tag_power_out_ts(tag) for tag in self._scoped_tags if tag in self._tag_power]
            if not arrays:
                return self.total_power_out_ts()
            if len(arrays) == 1:
                return arrays[0]
            result = arrays[0]
            for arr in arrays[1:]:
                result = result + arr
            return result
        return self.total_power_out_ts()

    def total_power_out_st(self) -> HighspyArray:
        """Total power leaving segment in s→t (with efficiency, summed across all tags)."""
        self._ensure_tags_initialized()
        arrays = [self.tag_power_out_st(tag) for tag in self._tags]
        if len(arrays) == 1:
            return arrays[0]
        result = arrays[0]
        for arr in arrays[1:]:
            result = result + arr
        return result

    def total_power_out_ts(self) -> HighspyArray:
        """Total power leaving segment in t→s (with efficiency, summed across all tags)."""
        self._ensure_tags_initialized()
        arrays = [self.tag_power_out_ts(tag) for tag in self._tags]
        if len(arrays) == 1:
            return arrays[0]
        result = arrays[0]
        for arr in arrays[1:]:
            result = result + arr
        return result


__all__ = ["EfficiencySegment", "EfficiencySegmentSpec"]
