"""Base class for connection segments.

Segments are composable transforms on a single direction of power flow.
Each segment derives its input flow from the segment before it and exposes
an output flow. Segments may add constraints and costs to the solver.

Flows are derived on every read rather than captured at construction, so a
constraint or cost that reads a flow records the upstream parameters that
shaped it, such as an efficiency, and is rebuilt when they change.

A segment instance belongs to one directional connection chain.
Bidirectional paths are modelled as two separate Connection elements,
each with its own segment chain.
"""

from collections.abc import Callable
from functools import reduce
import operator
from typing import Any

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

type FlowSource = Callable[[], dict[int, HighspyArray]]
"""Returns the per-tag flow entering a segment, derived from the current upstream parameters."""


class Segment:
    """A single-direction transform on power flow.

    Derives its input flow from a flow source and exposes an output flow.
    Identity by default — subclasses override `power_out` to transform the flow.
    """

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
        power_in: FlowSource,
    ) -> None:
        """Initialize segment with the source of its input flow.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance
            source_element: Connected source element reference
            target_element: Connected target element reference
            power_in: Source of the per-tag input power flows

        """
        self._segment_id = segment_id
        self._n_periods = n_periods
        self.periods = np.asarray(periods, dtype=float)
        self._solver = solver
        self._source_element = source_element
        self._target_element = target_element
        self._power_in_source = power_in

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
        """Per-tag input power flows."""
        return self._power_in_source()

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
