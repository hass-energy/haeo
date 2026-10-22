"""Base class for connection segments.

Segments are composable transforms on a single direction of power flow.
Each segment reads its input flow from its upstream, the segment before it,
and exposes an output flow. Segments may add constraints and costs to the solver.

Flows are read from upstream on every access rather than captured at
construction, so a constraint or cost that reads a flow records the upstream
parameters that shaped it, such as an efficiency, and is rebuilt when they change.

A segment instance belongs to one directional connection chain.
Bidirectional paths are modelled as two separate Connection elements,
each with its own segment chain.
"""

from dataclasses import dataclass
from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; segments only use these via hasattr/isinstance duck typing.
    Protocol,
)

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.component import ModelComponent
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.linear import LinearArray
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam
from custom_components.haeo.core.model.solver import Solver


class FlowProvider(Protocol):
    """Anything a segment can read its input flow from: another segment, or a connection's variables."""

    @property
    def power_out(self) -> dict[int, LinearArray]:
        """Per-tag power flowing out to the next segment."""
        ...


@dataclass(frozen=True)
class FlowVariables:
    """The upstream of a connection's first segment: its per-tag LP flow variables."""

    power_out: dict[int, LinearArray]


class Segment(ModelComponent):
    """A single-direction transform on power flow.

    Reads its input flow from its upstream and exposes an output flow.
    Identity by default — subclasses override `power_out` to transform the flow.
    """

    periods: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Solver,
        *,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize segment with the upstream it reads its input flow from.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            source_element: Connected source element reference
            target_element: Connected target element reference
            upstream: The segment or variables this segment's input flow comes from

        """
        self._segment_id = segment_id
        self._n_periods = n_periods
        self.periods = np.asarray(periods, dtype=float)
        self._solver = solver
        self._source_element = source_element
        self._target_element = target_element
        self._upstream = upstream

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
    def power_in(self) -> dict[int, LinearArray]:
        """Per-tag input power flows, read from upstream."""
        return self._upstream.power_out

    @property
    def total_power_in(self) -> LinearArray:
        """Sum of all tag input flows."""
        return LinearArray.sum_of(self.power_in.values())

    @property
    def power_out(self) -> dict[int, LinearArray]:
        """Per-tag output power flows. Identity by default."""
        return self.power_in

    @property
    def total_power_out(self) -> LinearArray:
        """Sum of all tag output flows."""
        return LinearArray.sum_of(self.power_out.values())

    def outputs(self) -> dict[str, OutputData]:
        """Return the segment's outputs that currently have a value, keyed by output name."""
        result: dict[str, OutputData] = {}
        for output_name, method in self.declared_outputs():
            if isinstance(output_data := method.get_output(self), OutputData):
                result[output_name] = output_data
        return result


__all__ = ["Segment"]
