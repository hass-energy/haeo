"""Base class for connection segments.

Segments are functional transforms on power flow expressions.
They receive input power (per-direction HighspyArrays), add constraints
and costs, and return output power (which may be the same expression
or a transformed one like input * efficiency).

The Connection creates the only LP variables — one set per direction.
Segments chain: connection_vars → segment1 → segment2 → ... → final output.

Most segments are identity transforms (return input unchanged):
- PassthroughSegment: no-op
- PricingSegment: adds cost, returns input
- PowerLimitSegment: adds constraint, returns input

Only EfficiencySegment transforms: returns input * efficiency.
SocPricingSegment creates auxiliary slack variables for its penalty.

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
    """Base class for connection segments.

    Segments receive input power expressions and return output power expressions.
    They may add constraints (power limits) or costs (pricing) to the solver.

    Subclasses implement apply() which receives per-direction power and returns
    the (possibly transformed) output power.
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

        # Set by apply() — the power expressions this segment operates on
        self._power_in_st: HighspyArray | None = None
        self._power_out_st: HighspyArray | None = None
        self._power_in_ts: HighspyArray | None = None
        self._power_out_ts: HighspyArray | None = None

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
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction."""
        return self._power_in_st  # type: ignore[return-value]  # Set by apply()

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction."""
        return self._power_out_st  # type: ignore[return-value]  # Set by apply()

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction."""
        return self._power_in_ts  # type: ignore[return-value]  # Set by apply()

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction."""
        return self._power_out_ts  # type: ignore[return-value]  # Set by apply()

    @abstractmethod
    def apply(
        self,
        power_st: HighspyArray,
        power_ts: HighspyArray,
    ) -> tuple[HighspyArray, HighspyArray]:
        """Apply this segment to the power flow.

        Receives input power expressions for each direction.
        Returns output power expressions (may be same or transformed).
        May add constraints and costs to the solver as side effects.

        Args:
            power_st: Power flow in source→target direction
            power_ts: Power flow in target→source direction

        Returns:
            Tuple of (output_st, output_ts) power expressions

        """
        ...

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Return all constraints from this segment.

        Discovers and calls all @constraint decorated methods.

        Returns:
            Dictionary mapping constraint method names to constraint objects

        """
        result: dict[str, highs_cons | list[highs_cons]] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, ReactiveConstraint):
                method = getattr(self, name)
                method()

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
