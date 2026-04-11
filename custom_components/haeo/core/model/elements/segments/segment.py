"""Base class for connection segments.

Segments are functional transforms on power flow expressions.
They receive input power (per-tag HighspyArray dicts), add constraints
and costs, and return output power (which may be the same expressions
or transformed ones like input * efficiency).

The Connection creates the only LP variables — per-tag per-direction.
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

# Default tag for untagged power (like VLAN 0)
DEFAULT_TAG: int = 0

# Type alias for per-tag power maps
type TagPowerMap = dict[int, HighspyArray]


class Segment(ABC):
    """Base class for connection segments.

    Segments receive per-tag input power dicts and return per-tag output power dicts.
    They may add constraints (power limits) or costs (pricing) to the solver.

    Subclasses implement apply() which receives per-tag per-direction power and returns
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
        """Initialize segment with common attributes."""
        self._segment_id = segment_id
        self._n_periods = n_periods
        self.periods = np.asarray(periods, dtype=float)
        self._solver = solver
        self._source_element = source_element
        self._target_element = target_element

        # Set by apply() — per-tag power maps
        self._power_in_st: TagPowerMap = {}
        self._power_in_ts: TagPowerMap = {}
        self._power_out_st: TagPowerMap = {}
        self._power_out_ts: TagPowerMap = {}

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

    # --- Aggregate power properties (sum across tags) ---

    @property
    def power_in_st(self) -> HighspyArray:
        """Total power entering segment in s→t (sum across all tags)."""
        return _sum_tag_map(self._power_in_st)

    @property
    def power_out_st(self) -> HighspyArray:
        """Total power leaving segment in s→t (sum across all tags)."""
        return _sum_tag_map(self._power_out_st)

    @property
    def power_in_ts(self) -> HighspyArray:
        """Total power entering segment in t→s (sum across all tags)."""
        return _sum_tag_map(self._power_in_ts)

    @property
    def power_out_ts(self) -> HighspyArray:
        """Total power leaving segment in t→s (sum across all tags)."""
        return _sum_tag_map(self._power_out_ts)

    # --- Per-tag access ---

    def tag_power_in_st(self, tag: int) -> HighspyArray:
        """Power entering segment in s→t for a specific tag."""
        return self._power_in_st[tag]

    def tag_power_out_st(self, tag: int) -> HighspyArray:
        """Power leaving segment in s→t for a specific tag."""
        return self._power_out_st[tag]

    def tag_power_in_ts(self, tag: int) -> HighspyArray:
        """Power entering segment in t→s for a specific tag."""
        return self._power_in_ts[tag]

    def tag_power_out_ts(self, tag: int) -> HighspyArray:
        """Power leaving segment in t→s for a specific tag."""
        return self._power_out_ts[tag]

    @abstractmethod
    def apply(
        self,
        power_st: TagPowerMap,
        power_ts: TagPowerMap,
    ) -> tuple[TagPowerMap, TagPowerMap]:
        """Apply this segment to the per-tag power flow.

        Args:
            power_st: Per-tag power flow in source→target direction
            power_ts: Per-tag power flow in target→source direction

        Returns:
            Tuple of (output_st, output_ts) per-tag power maps

        """
        ...

    def constraints(self) -> dict[str, highs_cons | list[highs_cons]]:
        """Return all constraints from this segment."""
        result: dict[str, highs_cons | list[highs_cons]] = {}
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, ReactiveConstraint):
                method = getattr(self, name)
                method()
                state_attr = f"_reactive_state_{name}"
                state = getattr(self, state_attr, None)
                if state is not None and "constraint" in state:
                    result[name] = state["constraint"]
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
        """Return aggregated cost expression from this segment."""
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


def _sum_tag_map(tag_map: TagPowerMap) -> HighspyArray:
    """Sum all values in a tag power map."""
    arrays = list(tag_map.values())
    if not arrays:
        msg = "Empty tag power map"
        raise RuntimeError(msg)
    if len(arrays) == 1:
        return arrays[0]
    result = arrays[0]
    for arr in arrays[1:]:
        result = result + arr
    return result


__all__ = ["DEFAULT_TAG", "Segment", "TagPowerMap"]
