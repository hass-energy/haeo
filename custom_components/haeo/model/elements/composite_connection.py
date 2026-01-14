"""Composite connection that chains multiple segments together.

A CompositeConnection wraps one or more ConnectionSegments and links them
with equality constraints. Power flows through segments in order for the
forward direction (source→target) and in reverse order for the reverse
direction (target→source).

Example:
    A connection with efficiency loss and power limit would chain:
    [EfficiencySegment, PowerLimitSegment]

    Forward: source_power → efficiency.in → efficiency.out → limit.in → limit.out → target_power
    Reverse: target_power → limit.in → limit.out → efficiency.in → efficiency.out → source_power
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import constraint, cost, output

from .segments import ConnectionSegment

type CompositeConnectionOutputName = Literal[
    "connection_power_source_target",
    "connection_power_target_source",
]

COMPOSITE_CONNECTION_OUTPUT_NAMES: Final[frozenset[CompositeConnectionOutputName]] = frozenset(
    (
        "connection_power_source_target",
        "connection_power_target_source",
    )
)


class CompositeConnection(Element[CompositeConnectionOutputName]):
    """Connection composed of chained segments.

    Each segment adds its own constraints and costs. Segments are linked by
    equality constraints so power flows through the chain. HiGHS presolve
    efficiently eliminates redundant variables.

    Forward direction (source→target) traverses segments in order.
    Reverse direction (target→source) traverses segments in reverse order.
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        source: str,
        target: str,
        segments: Sequence[ConnectionSegment],
    ) -> None:
        """Initialize a composite connection.

        Args:
            name: Name of the connection
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance
            source: Name of the source element
            target: Name of the target element
            segments: Sequence of segments to chain together

        """
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=COMPOSITE_CONNECTION_OUTPUT_NAMES,
        )

        self._source = source
        self._target = target
        self._segments = tuple(segments)

        # Validate we have at least one segment
        if not self._segments:
            msg = f"CompositeConnection {name} requires at least one segment"
            raise ValueError(msg)

    @property
    def source(self) -> str:
        """Return the name of the source element."""
        return self._source

    @property
    def target(self) -> str:
        """Return the name of the target element."""
        return self._target

    @property
    def segments(self) -> tuple[ConnectionSegment, ...]:
        """Return the segments in this composite connection."""
        return self._segments

    @property
    def power_source_target(self) -> HighspyArray:
        """Return power flowing from source to target for all periods.

        This is the power entering the first segment in the forward direction.
        """
        return self._segments[0].power_in_st

    @property
    def power_target_source(self) -> HighspyArray:
        """Return power flowing from target to source for all periods.

        This is the power entering the last segment in the reverse direction.
        """
        return self._segments[-1].power_in_ts

    @property
    def power_into_source(self) -> HighspyArray:
        """Return effective power flowing into the source element.

        This is the power leaving the first segment in reverse direction
        minus the power entering the first segment in forward direction.
        """
        first_seg = self._segments[0]
        return first_seg.power_out_ts - first_seg.power_in_st

    @property
    def power_into_target(self) -> HighspyArray:
        """Return effective power flowing into the target element.

        This is the power leaving the last segment in forward direction
        minus the power entering the last segment in reverse direction.
        """
        last_seg = self._segments[-1]
        return last_seg.power_out_st - last_seg.power_in_ts

    @constraint()
    def segment_chain_forward(self) -> list[highs_linear_expression] | None:
        """Link consecutive segments in the forward direction.

        Creates equality constraints: seg[i].power_out_st == seg[i+1].power_in_st
        """
        if len(self._segments) < 2:
            return None

        chain_constraints: list[highs_linear_expression] = []
        for i in range(len(self._segments) - 1):
            current_out = self._segments[i].power_out_st
            next_in = self._segments[i + 1].power_in_st
            chain_constraints.extend(current_out == next_in)

        return chain_constraints

    @constraint()
    def segment_chain_reverse(self) -> list[highs_linear_expression] | None:
        """Link consecutive segments in the reverse direction.

        Creates equality constraints: seg[i].power_out_ts == seg[i-1].power_in_ts
        (traversing in reverse order)
        """
        if len(self._segments) < 2:
            return None

        chain_constraints: list[highs_linear_expression] = []
        # Reverse direction: start from last segment, chain to first
        for i in range(len(self._segments) - 1, 0, -1):
            current_out = self._segments[i].power_out_ts
            prev_in = self._segments[i - 1].power_in_ts
            chain_constraints.extend(current_out == prev_in)

        return chain_constraints

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Return all constraints including segment constraints."""
        result = super().constraints()

        # Add constraints from each segment
        for segment in self._segments:
            segment_constraints = segment.add_constraints()
            result.update(segment_constraints)

        return result

    @cost
    def segment_costs(self) -> highs_linear_expression | None:
        """Aggregate costs from all segments."""
        cost_terms: list[Any] = []
        for segment in self._segments:
            if (segment_cost := segment.costs()) is not None:
                cost_terms.append(segment_cost)

        if not cost_terms:
            return None
        if len(cost_terms) == 1:
            return cost_terms[0]
        return sum(cost_terms[1:], cost_terms[0])

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

    def outputs(self) -> Mapping[CompositeConnectionOutputName, OutputData]:
        """Return outputs including segment outputs."""
        result = dict(super().outputs())

        # Add outputs from each segment
        for segment in self._segments:
            segment_outputs = segment.outputs()
            result.update(segment_outputs)  # type: ignore[arg-type]

        return result


__all__ = [
    "COMPOSITE_CONNECTION_OUTPUT_NAMES",
    "CompositeConnection",
    "CompositeConnectionOutputName",
]
