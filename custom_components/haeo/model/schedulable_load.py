"""Schedulable load element for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np

from .const import OutputType
from .element import Element
from .output_data import OutputData

# Type for schedulable load constraint names
type SchedulableLoadConstraintName = Literal[
    "schedulable_load_power_balance",
    "schedulable_load_left_edge_boundary",
    "schedulable_load_left_edge_start",
    "schedulable_load_right_edge_boundary",
    "schedulable_load_right_edge_end",
    "schedulable_load_overlap_min",
    "schedulable_load_overlap_max",
    "schedulable_load_total_overlap",
    "schedulable_load_earliest_start",
    "schedulable_load_latest_start",
]

# Type for all schedulable load output names
type SchedulableLoadOutputName = (
    Literal[
        "schedulable_load_power_consumed",
        "schedulable_load_start_time",
    ]
    | SchedulableLoadConstraintName
)

# Constraint names
SCHEDULABLE_LOAD_CONSTRAINT_NAMES: Final[frozenset[SchedulableLoadConstraintName]] = frozenset(
    (
        SCHEDULABLE_LOAD_POWER_BALANCE := "schedulable_load_power_balance",
        SCHEDULABLE_LOAD_LEFT_EDGE_BOUNDARY := "schedulable_load_left_edge_boundary",
        SCHEDULABLE_LOAD_LEFT_EDGE_START := "schedulable_load_left_edge_start",
        SCHEDULABLE_LOAD_RIGHT_EDGE_BOUNDARY := "schedulable_load_right_edge_boundary",
        SCHEDULABLE_LOAD_RIGHT_EDGE_END := "schedulable_load_right_edge_end",
        SCHEDULABLE_LOAD_OVERLAP_MIN := "schedulable_load_overlap_min",
        SCHEDULABLE_LOAD_OVERLAP_MAX := "schedulable_load_overlap_max",
        SCHEDULABLE_LOAD_TOTAL_OVERLAP := "schedulable_load_total_overlap",
        SCHEDULABLE_LOAD_EARLIEST_START := "schedulable_load_earliest_start",
        SCHEDULABLE_LOAD_LATEST_START := "schedulable_load_latest_start",
    )
)

# Power constraints (for shadow price units)
SCHEDULABLE_LOAD_POWER_CONSTRAINTS: Final[frozenset[SchedulableLoadConstraintName]] = frozenset(
    (SCHEDULABLE_LOAD_POWER_BALANCE,)
)

# Output names
SCHEDULABLE_LOAD_OUTPUT_NAMES: Final[frozenset[SchedulableLoadOutputName]] = frozenset(
    (
        SCHEDULABLE_LOAD_POWER_CONSUMED := "schedulable_load_power_consumed",
        SCHEDULABLE_LOAD_START_TIME := "schedulable_load_start_time",
        *SCHEDULABLE_LOAD_CONSTRAINT_NAMES,
    )
)

# Tolerance for detecting non-zero overlap values
OVERLAP_TOLERANCE: Final[float] = 1e-9


class SchedulableLoad(Element[SchedulableLoadOutputName, SchedulableLoadConstraintName]):
    """Schedulable load element for electrical system modeling.

    Models a deferrable load that must run for a fixed duration at a fixed power,
    with the optimizer choosing the optimal start time within a scheduling window.

    Uses an overlap-based formulation to model power consumption in each period:
    - left_edge[t] = max(b_t, s) - where active region starts in period t
    - right_edge[t] = min(b_{t+1}, s+d) - where active region ends in period t
    - overlap[t] = right_edge[t] - left_edge[t] - active time in period t
    - power[t] = P * overlap[t] / period[t] - average power in period t

    The total overlap must equal the load duration, ensuring the full energy
    requirement is met.
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        power: float,
        duration: float,
        earliest_start: float,
        latest_start: float,
    ) -> None:
        """Initialize a schedulable load element.

        Args:
            name: Name of the schedulable load
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            power: Load power consumption in kW
            duration: Load run duration in hours
            earliest_start: Earliest allowed start time in hours from horizon start
            latest_start: Latest allowed start time in hours from horizon start

        """
        super().__init__(name=name, periods=periods, solver=solver)
        n_periods = self.n_periods

        # Validate parameters
        if power < 0:
            msg = f"power must be non-negative, got {power}"
            raise ValueError(msg)
        if duration < 0:
            msg = f"duration must be non-negative, got {duration}"
            raise ValueError(msg)
        if earliest_start < 0:
            msg = f"earliest_start must be non-negative, got {earliest_start}"
            raise ValueError(msg)
        if latest_start < earliest_start:
            msg = f"latest_start ({latest_start}) must be >= earliest_start ({earliest_start})"
            raise ValueError(msg)

        # Store parameters
        self.power = power
        self.duration = duration
        self.earliest_start = earliest_start
        self.latest_start = latest_start

        # Total energy consumed by the load
        self.total_energy = power * duration

        # Calculate cumulative time boundaries: b_0 = 0, b_t = sum of periods up to t
        # Shape: (n_periods + 1,) for fence-post pattern
        self.boundaries = np.concatenate([[0.0], np.cumsum(self.periods)])
        self.horizon = float(self.boundaries[-1])

        # Decision variable: start time
        self.start_time_var = solver.addVariable(
            lb=earliest_start,
            ub=latest_start,
            name=f"{name}_start_time",
        )

        # Auxiliary variables for overlap calculation
        # left_edge[t] = max(b_t, s) - where active region starts in period t
        self.left_edge = solver.addVariables(
            n_periods,
            lb=0.0,
            ub=self.horizon,
            name_prefix=f"{name}_left_edge_",
            out_array=True,
        )

        # right_edge[t] = min(b_{t+1}, s+d) - where active region ends in period t
        self.right_edge = solver.addVariables(
            n_periods,
            lb=0.0,
            ub=self.horizon + duration,
            name_prefix=f"{name}_right_edge_",
            out_array=True,
        )

        # overlap[t] = time the load is active in period t
        self.overlap = solver.addVariables(
            n_periods,
            lb=0.0,
            name_prefix=f"{name}_overlap_",
            out_array=True,
        )

    def build_constraints(self) -> None:
        """Build constraints for the schedulable load.

        Models the overlap between the load's active window [s, s+d] and each
        period's time interval [b_t, b_{t+1}] using auxiliary variables:

        - left_edge[t] >= b_t, left_edge[t] >= s (models max(b_t, s))
        - right_edge[t] <= b_{t+1}, right_edge[t] <= s+d (models min(b_{t+1}, s+d))
        - overlap[t] >= right_edge[t] - left_edge[t] (active time in period)
        - sum(overlap) = duration (total active time must equal duration)
        - connection_power[t] * period[t] = -P * overlap[t] (power balance from overlap)

        The max/min relaxation works correctly because:
        - left_edge is minimized to achieve larger overlap
        - right_edge is maximized to achieve larger overlap
        - Total overlap constraint forces exactly 'duration' hours of activity
        """
        h = self._solver

        # Left edge is bounded below by both period start and start time
        self._constraints[SCHEDULABLE_LOAD_LEFT_EDGE_BOUNDARY] = h.addConstrs(self.left_edge >= self.boundaries[:-1])
        self._constraints[SCHEDULABLE_LOAD_LEFT_EDGE_START] = h.addConstrs(self.left_edge >= self.start_time_var)

        # Right edge is bounded above by both period end and start time + duration
        self._constraints[SCHEDULABLE_LOAD_RIGHT_EDGE_BOUNDARY] = h.addConstrs(self.right_edge <= self.boundaries[1:])
        self._constraints[SCHEDULABLE_LOAD_RIGHT_EDGE_END] = h.addConstrs(
            self.right_edge <= self.start_time_var + self.duration
        )

        # Overlap is at least the difference between right and left edges
        self._constraints[SCHEDULABLE_LOAD_OVERLAP_MIN] = h.addConstrs(self.overlap >= self.right_edge - self.left_edge)

        # Overlap cannot exceed period length
        self._constraints[SCHEDULABLE_LOAD_OVERLAP_MAX] = h.addConstrs(self.overlap <= self.periods)

        # Total overlap must equal duration (forces the load to run for exactly 'duration' hours)
        self._constraints[SCHEDULABLE_LOAD_TOTAL_OVERLAP] = h.addConstr(Highs.qsum(self.overlap) == self.duration)

        # Start time bounds (explicit constraints for shadow price extraction)
        self._constraints[SCHEDULABLE_LOAD_EARLIEST_START] = h.addConstr(self.start_time_var >= self.earliest_start)
        self._constraints[SCHEDULABLE_LOAD_LATEST_START] = h.addConstr(self.start_time_var <= self.latest_start)

        # Power balance: connection_power * period = -power * overlap
        # Negative because load consumes power (power flows from connection into load)
        self._constraints[SCHEDULABLE_LOAD_POWER_BALANCE] = h.addConstrs(
            self.connection_power() * self.periods == -self.power * self.overlap
        )

    def cost(self) -> Sequence[highs_linear_expression]:
        """Return the cost expressions of the schedulable load.

        The schedulable load has no inherent cost - costs are applied through
        connections linking the load to the network.
        """
        return []

    def _compute_effective_start_time(self) -> float:
        """Compute effective start time from the power profile.

        Since the LP relaxation may not perfectly tie start_time_var to the power
        profile, we derive the effective start time from where power actually begins.

        Returns:
            The effective start time in hours.

        """
        overlap_values = self.extract_values(self.overlap)
        boundaries = self.boundaries

        # Find the weighted center of mass of the active period
        # This gives a meaningful "start time" interpretation
        if self.duration == 0:
            return float(self._solver.val(self.start_time_var))

        # Find where activity begins (first period with positive overlap)
        for t, overlap in enumerate(overlap_values):
            if overlap > OVERLAP_TOLERANCE:
                # Activity starts in this period
                # Effective start = period start + (period_length - overlap)
                # This accounts for partial overlap at the start
                period_start = float(boundaries[t])
                period_length = float(self.periods[t])
                # If overlap < period_length, the load started partway through
                # start_time = period_end - overlap = b_{t+1} - overlap
                effective_start = period_start + (period_length - overlap)
                return max(effective_start, self.earliest_start)

        # No activity found, return the variable value
        return float(self._solver.val(self.start_time_var))

    def outputs(self) -> Mapping[SchedulableLoadOutputName, OutputData]:
        """Return schedulable load output specifications."""
        # Compute power consumption from overlap: power[t] = P * overlap[t] / period[t]
        overlap_values = self.extract_values(self.overlap)
        power_values = tuple(self.power * o / p for o, p in zip(overlap_values, self.periods, strict=True))

        outputs: dict[SchedulableLoadOutputName, OutputData] = {
            SCHEDULABLE_LOAD_POWER_CONSUMED: OutputData(
                type=OutputType.POWER,
                unit="kW",
                values=power_values,
                direction="-",
            ),
            SCHEDULABLE_LOAD_START_TIME: OutputData(
                type=OutputType.DURATION,
                unit="h",
                values=(self._compute_effective_start_time(),),
            ),
        }

        # Add constraint shadow prices
        for constraint_name in self._constraints:
            unit = "$/kW" if constraint_name in SCHEDULABLE_LOAD_POWER_CONSTRAINTS else "$/kWh"
            outputs[constraint_name] = OutputData(
                type=OutputType.SHADOW_PRICE,
                unit=unit,
                values=self.extract_values(self._constraints[constraint_name]),
            )

        return outputs
