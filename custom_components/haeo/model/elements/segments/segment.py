"""Base class for connection segments.

Segments are modular components that can be chained together to form
composite connections. Each segment owns LP variables for power flow
in both directions:
- power_in_st / power_out_st: Source→Target direction
- power_in_ts / power_out_ts: Target→Source direction

Segments are reactive-aware: they can use TrackedParam for parameters and
@constraint/@cost decorators for methods. This enables warm-start optimization
where parameter changes automatically invalidate and rebuild affected constraints.
"""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.reactive import ReactiveConstraint, ReactiveCost


class Segment:
    """Base class for connection segments.

    Each segment owns its own LP power variables and can use the reactive
    infrastructure (TrackedParam, @constraint, @cost) for warm-start support.

    Subclasses implement specific modifiers:
    - EfficiencySegment: applies efficiency losses (power_out = power_in * η)
    - PowerLimitSegment: limits maximum power flow with optional time-slice
    - PricingSegment: adds transfer cost to objective
    """

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
    ) -> None:
        """Initialize a segment with LP variables.

        Args:
            segment_id: Unique identifier for naming LP variables
            n_periods: Number of optimization periods
            periods: Time period durations in hours
            solver: HiGHS solver instance

        """
        self._segment_id = segment_id
        self._n_periods = n_periods
        self._periods = periods
        self._solver = solver

        # Create power variables for both directions
        # Source→Target direction
        self._power_in_st = solver.addVariables(
            n_periods, lb=0, name_prefix=f"{segment_id}_in_st_", out_array=True
        )
        self._power_out_st = solver.addVariables(
            n_periods, lb=0, name_prefix=f"{segment_id}_out_st_", out_array=True
        )
        # Target→Source direction
        self._power_in_ts = solver.addVariables(
            n_periods, lb=0, name_prefix=f"{segment_id}_in_ts_", out_array=True
        )
        self._power_out_ts = solver.addVariables(
            n_periods, lb=0, name_prefix=f"{segment_id}_out_ts_", out_array=True
        )

    @property
    def segment_id(self) -> str:
        """Return the segment identifier."""
        return self._segment_id

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return self._n_periods

    @property
    def periods(self) -> NDArray[np.floating[Any]]:
        """Return time period durations in hours."""
        return self._periods

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_in_st

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction."""
        return self._power_out_st

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_in_ts

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction."""
        return self._power_out_ts

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
