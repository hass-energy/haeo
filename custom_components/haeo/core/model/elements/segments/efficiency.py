"""Efficiency segment — applies losses to power flow."""

from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; segments only use these via hasattr/isinstance duck typing.
    Literal,
    NotRequired,
)

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.reactive import TrackedParam, computed
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .segment import FlowProvider, Segment


class EfficiencySegmentSpec(TypedDict):
    """Specification for creating an EfficiencySegment.

    Directional fields are resolved by the Connection into `efficiency`.
    """

    segment_type: Literal["efficiency"]
    efficiency: NotRequired[NDArray[np.float64] | float | None]
    # Directional aliases — resolved by Connection, not used by segment directly
    efficiency_source_target: NotRequired[NDArray[np.float64] | float | None]
    efficiency_target_source: NotRequired[NDArray[np.float64] | float | None]


class EfficiencySegment(Segment):
    """Applies efficiency losses: output = input * efficiency."""

    efficiency: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Highs,
        *,
        spec: EfficiencySegmentSpec,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize efficiency segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            upstream=upstream,
        )
        self.efficiency = broadcast_to_sequence(spec.get("efficiency"), self._n_periods)

    @property
    def power_out(self) -> dict[int, HighspyArray]:
        """Per-tag output with efficiency applied to each tag flow."""
        return self.efficient_flows()

    @computed
    def efficient_flows(self) -> dict[int, HighspyArray]:
        """Per-tag flows with efficiency applied, rebuilt only when the efficiency or upstream flows change."""
        efficiency = self.efficiency
        if efficiency is None:
            return self.power_in
        return {tag: flow * efficiency for tag, flow in self.power_in.items()}


__all__ = ["EfficiencySegment", "EfficiencySegmentSpec"]
