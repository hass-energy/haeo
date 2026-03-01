"""Base class for connection segments.

Segments are modular components that can be chained together to form
connections. Each segment exposes power flow properties that the Connection
uses to link segments together.

The linking protocol:
- power_in_st / power_in_ts: Power entering this segment
- power_out_st / power_out_ts: Power leaving this segment

For simple segments (no losses), in == out (same variable).
For segments with losses (efficiency), out = in * factor (separate variables with constraint).

Segments are reactive-aware: they can use TrackedParam for parameters and
@constraint/@cost decorators for methods.
"""

from abc import ABC, abstractmethod
from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons
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
