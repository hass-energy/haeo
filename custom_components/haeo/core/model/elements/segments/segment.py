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
from functools import reduce
import operator
from typing import (
    Protocol,
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; segments only use these via hasattr/isinstance duck typing.
)

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import (
    OutputMethod,
    ReactiveConstraint,
    ReactiveCost,
    TrackedParam,
    applied_constraint,
    cost,
)


class FlowProvider(Protocol):
    """Anything a segment can read its input flow from: another segment, or a connection's variables."""

    @property
    def power_out(self) -> dict[int, HighspyArray]:
        """Per-tag power flowing out to the next segment."""
        ...


@dataclass(frozen=True)
class FlowVariables:
    """The upstream of a connection's first segment: its per-tag LP flow variables."""

    power_out: dict[int, HighspyArray]


class Segment:
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
        solver: Highs,
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
    def power_in(self) -> dict[int, HighspyArray]:
        """Per-tag input power flows, read from upstream."""
        return self._upstream.power_out

    @property
    def total_power_in(self) -> HighspyArray:
        """Sum of all tag input flows."""
        return reduce(operator.add, self.power_in.values())

    @property
    def power_out(self) -> dict[int, HighspyArray]:
        """Per-tag output power flows. Identity by default."""
        return self.power_in

    @property
    def total_power_out(self) -> HighspyArray:
        """Sum of all tag output flows."""
        return reduce(operator.add, self.power_out.values())

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Return all constraints from this segment."""
        result: dict[str, highs_cons | list[highs_cons]] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, ReactiveConstraint):
                method = getattr(self, name)
                method()
                if (cons := applied_constraint(self, name)) is not None:
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

    @cost
    def cost(self) -> highs_linear_expression | None:
        """Return aggregated primary cost expression from this segment."""
        # Access decorator's internal name to skip self in dir() loop
        this_method_name = type(self).cost._name  # type: ignore[attr-defined]  # noqa: SLF001 (_name is set by ReactiveCost.__set_name__, not part of public API)

        costs: list[highs_linear_expression] = []
        for name in dir(type(self)):
            if name == this_method_name:
                continue
            attr = getattr(type(self), name, None)
            if not isinstance(attr, ReactiveCost):
                continue
            method = getattr(self, name)
            if (cost_value := method()) is not None:
                costs.append(cost_value)

        if not costs:
            return None
        if len(costs) == 1:
            return costs[0]
        return sum(costs[1:], costs[0])


__all__ = ["Segment"]
