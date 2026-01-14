"""Connection segments for composable power flow modifiers.

Segments are individual modifiers that can be chained together to form
composite connections. Each segment owns its own LP variables for power_in
and power_out, and adds its specific constraints/costs.

The chain works bidirectionally:
- Forward (source→target): power flows through segments in order
- Reverse (target→source): power flows through segments in reverse order

Segments are linked by equality constraints: seg[i].power_out_* == seg[i+1].power_in_*
HiGHS presolve efficiently eliminates redundant variables from these chains.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.output_data import OutputData

# Type alias for numeric values that can be broadcast to per-period arrays
type NumericParam = float | Sequence[float] | NDArray[np.floating[Any]]


class ConnectionSegment(ABC):
    """Base class for connection segment modifiers.

    Each segment represents a stage in the power transfer process between
    two elements. Segments own their own LP variables for power_in and power_out
    in both directions, and can add constraints and costs.

    Subclasses implement specific modifiers:
    - EfficiencySegment: applies efficiency losses (power_out = power_in * η)
    - PowerLimitSegment: limits maximum power flow
    - PricingSegment: adds transfer cost to objective
    - TimeSliceSegment: prevents simultaneous bidirectional flow at capacity
    """

    def __init__(
        self,
        segment_id: str,
        periods: Sequence[float] | NDArray[np.floating[Any]],
        solver: Highs,
    ) -> None:
        """Initialize a segment with LP variables.

        Args:
            segment_id: Unique identifier for naming LP variables
            periods: Time period durations in hours
            solver: HiGHS solver instance

        """
        self._segment_id = segment_id
        self._periods: NDArray[np.floating[Any]] = np.asarray(periods)
        self._solver = solver
        n_periods = len(self._periods)

        # Create power variables for both directions
        # Source→Target direction
        self._power_in_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_in_st_", out_array=True)
        self._power_out_st = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_out_st_", out_array=True)
        # Target→Source direction
        self._power_in_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_in_ts_", out_array=True)
        self._power_out_ts = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_out_ts_", out_array=True)

    @property
    def segment_id(self) -> str:
        """Return the segment identifier."""
        return self._segment_id

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self._periods)

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

    @abstractmethod
    def segment_type(self) -> str:
        """Return the type name for this segment (e.g., 'efficiency', 'limit')."""

    @abstractmethod
    def add_constraints(self) -> dict[str, list[highs_cons]]:
        """Add segment-specific constraints to the solver.

        Returns:
            Dictionary mapping constraint names to constraint objects

        """

    def costs(self) -> highs_linear_expression | None:
        """Return cost expression for this segment, or None if no cost."""
        return None

    def outputs(self) -> Mapping[str, OutputData]:
        """Return output data from this segment."""
        return {}


class PassthroughSegment(ConnectionSegment):
    """Lossless passthrough segment (power_out == power_in).

    This is the simplest segment - just passes power through unchanged.
    Used as the identity operation in chains.
    """

    def segment_type(self) -> str:
        """Return 'passthrough' as the segment type."""
        return "passthrough"

    def add_constraints(self) -> dict[str, list[highs_cons]]:
        """Add passthrough constraints: power_out == power_in for both directions."""
        h = self._solver
        constraints: dict[str, list[highs_cons]] = {}

        # Source→Target: output equals input
        st_passthrough = list(self._power_out_st == self._power_in_st)
        constraints[f"{self._segment_id}_passthrough_st"] = h.addConstrs(st_passthrough)

        # Target→Source: output equals input
        ts_passthrough = list(self._power_out_ts == self._power_in_ts)
        constraints[f"{self._segment_id}_passthrough_ts"] = h.addConstrs(ts_passthrough)

        return constraints


class EfficiencySegment(ConnectionSegment):
    """Segment that applies efficiency losses to power transfer.

    Power is reduced by the efficiency factor: power_out = power_in * efficiency
    Efficiency is applied in the direction of flow (forward reduces target-bound
    power, reverse reduces source-bound power).
    """

    def __init__(
        self,
        segment_id: str,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        efficiency_st: NumericParam,
        efficiency_ts: NumericParam | None = None,
    ) -> None:
        """Initialize efficiency segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            periods: Time period durations in hours
            solver: HiGHS solver instance
            efficiency_st: Efficiency (0-1) for source→target direction
            efficiency_ts: Efficiency (0-1) for target→source direction.
                          If None, uses same as efficiency_st.

        """
        super().__init__(segment_id, periods, solver)
        n_periods = self.n_periods

        # Broadcast efficiency to array
        if isinstance(efficiency_st, (int, float)):
            self._efficiency_st = np.full(n_periods, efficiency_st)
        else:
            self._efficiency_st = np.asarray(efficiency_st)

        if efficiency_ts is None:
            self._efficiency_ts = self._efficiency_st
        elif isinstance(efficiency_ts, (int, float)):
            self._efficiency_ts = np.full(n_periods, efficiency_ts)
        else:
            self._efficiency_ts = np.asarray(efficiency_ts)

    def segment_type(self) -> str:
        """Return 'efficiency' as the segment type."""
        return "efficiency"

    def add_constraints(self) -> dict[str, list[highs_cons]]:
        """Add efficiency constraints: power_out == power_in * efficiency."""
        h = self._solver
        constraints: dict[str, list[highs_cons]] = {}

        # Source→Target: apply efficiency loss
        st_efficiency = list(self._power_out_st == self._power_in_st * self._efficiency_st)
        constraints[f"{self._segment_id}_efficiency_st"] = h.addConstrs(st_efficiency)

        # Target→Source: apply efficiency loss
        ts_efficiency = list(self._power_out_ts == self._power_in_ts * self._efficiency_ts)
        constraints[f"{self._segment_id}_efficiency_ts"] = h.addConstrs(ts_efficiency)

        return constraints


class PowerLimitSegment(ConnectionSegment):
    """Segment that limits maximum power flow.

    Adds upper bound constraints on power entering the segment.
    Can optionally fix power to exact values (equality constraint).
    """

    def __init__(
        self,
        segment_id: str,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        max_power_st: NumericParam | None = None,
        max_power_ts: NumericParam | None = None,
        fixed_power: bool = False,
    ) -> None:
        """Initialize power limit segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            periods: Time period durations in hours
            solver: HiGHS solver instance
            max_power_st: Maximum power in source→target direction (kW)
            max_power_ts: Maximum power in target→source direction (kW)
            fixed_power: If True, power is fixed to max values (equality)

        """
        super().__init__(segment_id, periods, solver)
        n_periods = self.n_periods
        self._fixed_power = fixed_power

        # Broadcast max_power to arrays
        self._max_power_st: NDArray[np.float64] | None = None
        self._max_power_ts: NDArray[np.float64] | None = None

        if max_power_st is not None:
            if isinstance(max_power_st, (int, float)):
                self._max_power_st = np.full(n_periods, max_power_st)
            else:
                self._max_power_st = np.asarray(max_power_st)

        if max_power_ts is not None:
            if isinstance(max_power_ts, (int, float)):
                self._max_power_ts = np.full(n_periods, max_power_ts)
            else:
                self._max_power_ts = np.asarray(max_power_ts)

    def segment_type(self) -> str:
        """Return 'limit' as the segment type."""
        return "limit"

    def add_constraints(self) -> dict[str, list[highs_cons]]:
        """Add power limit constraints."""
        h = self._solver
        constraints: dict[str, list[highs_cons]] = {}

        # First add passthrough constraints (output == input)
        st_passthrough = list(self._power_out_st == self._power_in_st)
        constraints[f"{self._segment_id}_passthrough_st"] = h.addConstrs(st_passthrough)

        ts_passthrough = list(self._power_out_ts == self._power_in_ts)
        constraints[f"{self._segment_id}_passthrough_ts"] = h.addConstrs(ts_passthrough)

        # Then add limit constraints
        if self._max_power_st is not None:
            if self._fixed_power:
                st_limit = list(self._power_in_st == self._max_power_st)
            else:
                st_limit = list(self._power_in_st <= self._max_power_st)
            constraints[f"{self._segment_id}_limit_st"] = h.addConstrs(st_limit)

        if self._max_power_ts is not None:
            if self._fixed_power:
                ts_limit = list(self._power_in_ts == self._max_power_ts)
            else:
                ts_limit = list(self._power_in_ts <= self._max_power_ts)
            constraints[f"{self._segment_id}_limit_ts"] = h.addConstrs(ts_limit)

        return constraints


class PricingSegment(ConnectionSegment):
    """Segment that adds transfer pricing to the objective function.

    Adds cost = power * price * period_duration for each direction.
    """

    def __init__(
        self,
        segment_id: str,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        price_st: NumericParam | None = None,
        price_ts: NumericParam | None = None,
    ) -> None:
        """Initialize pricing segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            periods: Time period durations in hours
            solver: HiGHS solver instance
            price_st: Price in $/kWh for source→target flow
            price_ts: Price in $/kWh for target→source flow

        """
        super().__init__(segment_id, periods, solver)
        n_periods = self.n_periods

        # Broadcast prices to arrays
        self._price_st: NDArray[np.float64] | None = None
        self._price_ts: NDArray[np.float64] | None = None

        if price_st is not None:
            if isinstance(price_st, (int, float)):
                self._price_st = np.full(n_periods, price_st)
            else:
                self._price_st = np.asarray(price_st)

        if price_ts is not None:
            if isinstance(price_ts, (int, float)):
                self._price_ts = np.full(n_periods, price_ts)
            else:
                self._price_ts = np.asarray(price_ts)

    def segment_type(self) -> str:
        """Return 'pricing' as the segment type."""
        return "pricing"

    def add_constraints(self) -> dict[str, list[highs_cons]]:
        """Add passthrough constraints (pricing doesn't modify power flow)."""
        h = self._solver
        constraints: dict[str, list[highs_cons]] = {}

        # Passthrough: output equals input
        st_passthrough = list(self._power_out_st == self._power_in_st)
        constraints[f"{self._segment_id}_passthrough_st"] = h.addConstrs(st_passthrough)

        ts_passthrough = list(self._power_out_ts == self._power_in_ts)
        constraints[f"{self._segment_id}_passthrough_ts"] = h.addConstrs(ts_passthrough)

        return constraints

    def costs(self) -> highs_linear_expression | None:
        """Return cost expression for transfer pricing."""
        cost_terms: list[highs_linear_expression] = []

        if self._price_st is not None:
            cost_terms.append(Highs.qsum(self._power_in_st * self._price_st * self._periods))

        if self._price_ts is not None:
            cost_terms.append(Highs.qsum(self._power_in_ts * self._price_ts * self._periods))

        if not cost_terms:
            return None
        return Highs.qsum(cost_terms)


class TimeSliceSegment(ConnectionSegment):
    """Segment that prevents simultaneous bidirectional power flow at capacity.

    Adds constraint: (power_st / max_st) + (power_ts / max_ts) <= 1
    This prevents the connection from carrying full power in both directions
    at the same time.
    """

    def __init__(
        self,
        segment_id: str,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        capacity_st: NumericParam,
        capacity_ts: NumericParam,
    ) -> None:
        """Initialize time slice segment.

        Args:
            segment_id: Unique identifier for naming LP variables
            periods: Time period durations in hours
            solver: HiGHS solver instance
            capacity_st: Reference capacity for source→target normalization (kW)
            capacity_ts: Reference capacity for target→source normalization (kW)

        """
        super().__init__(segment_id, periods, solver)
        n_periods = self.n_periods

        # Broadcast capacities to arrays
        if isinstance(capacity_st, (int, float)):
            self._capacity_st = np.full(n_periods, capacity_st)
        else:
            self._capacity_st = np.asarray(capacity_st)

        if isinstance(capacity_ts, (int, float)):
            self._capacity_ts = np.full(n_periods, capacity_ts)
        else:
            self._capacity_ts = np.asarray(capacity_ts)

    def segment_type(self) -> str:
        """Return 'time_slice' as the segment type."""
        return "time_slice"

    def add_constraints(self) -> dict[str, list[highs_cons]]:
        """Add time slice and passthrough constraints."""
        h = self._solver
        constraints: dict[str, list[highs_cons]] = {}

        # Passthrough: output equals input
        st_passthrough = list(self._power_out_st == self._power_in_st)
        constraints[f"{self._segment_id}_passthrough_st"] = h.addConstrs(st_passthrough)

        ts_passthrough = list(self._power_out_ts == self._power_in_ts)
        constraints[f"{self._segment_id}_passthrough_ts"] = h.addConstrs(ts_passthrough)

        # Time slice constraint: normalized sum <= 1
        # For periods with zero capacity, np.divide gives 0 (where=False)
        normalized_st = self._power_in_st * np.divide(
            1.0,
            self._capacity_st,
            out=np.zeros(self.n_periods),
            where=self._capacity_st > 0,
        )
        normalized_ts = self._power_in_ts * np.divide(
            1.0,
            self._capacity_ts,
            out=np.zeros(self.n_periods),
            where=self._capacity_ts > 0,
        )
        time_slice = list(normalized_st + normalized_ts <= 1.0)
        constraints[f"{self._segment_id}_time_slice"] = h.addConstrs(time_slice)

        return constraints


__all__ = [
    "ConnectionSegment",
    "EfficiencySegment",
    "NumericParam",
    "PassthroughSegment",
    "PowerLimitSegment",
    "PricingSegment",
    "TimeSliceSegment",
]
