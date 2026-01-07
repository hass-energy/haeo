"""Schedulable load element for electrical system modeling."""

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Final, Literal

from highspy import Highs, HighsVarType
from highspy.highs import highs_cons, highs_linear_expression
import numpy as np

from .const import OutputType
from .element import Element
from .output_data import OutputData


class IntegerMode(Enum):
    """Integer variable mode for schedulable load candidates.

    Controls how candidate selection variables are treated in the optimization:

    - NONE: All candidates are continuous [0,1]. Fastest option but may give
      fractional solutions when power limits or other constraints couple
      decision variables.

    - FIRST: Only the first candidate is integer (binary). Ensures the immediate
      decision is crisp while leaving future decisions flexible. Default choice
      with negligible performance overhead (~1x).

    - ALL: All candidates are integer (binary). Full MILP formulation with
      guaranteed integer solutions but ~10x solve time overhead.
    """

    NONE = "none"
    FIRST = "first"
    ALL = "all"


# Type for schedulable load constraint names
type SchedulableLoadConstraintName = Literal[
    "schedulable_load_power_balance",
    "schedulable_load_choice",
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
        SCHEDULABLE_LOAD_CHOICE := "schedulable_load_choice",
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

# Tolerance for detecting non-zero choice weights
WEIGHT_TOLERANCE: Final[float] = 1e-6


class SchedulableLoad(Element[SchedulableLoadOutputName, SchedulableLoadConstraintName]):
    """Schedulable load element for electrical system modeling.

    Models a deferrable load that must run for a fixed duration at a fixed power,
    with the optimizer choosing the optimal start time within a scheduling window.

    Uses period-boundary selection: one candidate per period boundary within the
    scheduling window, with energy "smeared in time" into overlapping periods.
    LP often produces integer solutions for simple cases, but power limits, ramp
    constraints, or multiple loads can cause fractional solutions.

    Use the `integer_mode` parameter to control integer variable behavior:

    - NONE: Pure LP (may be fractional with power limits or coupling)
    - FIRST: First candidate is binary, rest continuous (default, ~1x overhead)
    - ALL: All candidates binary (~10x overhead, guaranteed integer)
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
        integer_mode: IntegerMode = IntegerMode.FIRST,
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
            integer_mode: How to treat candidate selection variables:
                - NONE: All continuous (pure LP, may be fractional)
                - FIRST: First candidate binary, rest continuous (default)
                - ALL: All candidates binary (full MILP)

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
        self.integer_mode = integer_mode

        # Total energy consumed by the load
        self.total_energy = power * duration

        # Calculate cumulative time boundaries: b_0 = 0, b_t = sum of periods up to t
        # Shape: (n_periods + 1,) for fence-post pattern
        self.boundaries = np.concatenate([[0.0], np.cumsum(self.periods)])
        self.horizon = float(self.boundaries[-1])

        # Generate candidate start times: period boundaries within the scheduling window
        # where the load can complete before the horizon ends.
        self.candidates = tuple(
            float(b) for b in self.boundaries if earliest_start <= b <= latest_start and b + duration <= self.horizon
        )
        n_candidates = len(self.candidates)

        # Precompute energy profiles for each candidate start time.
        # profiles[k][t] = energy consumed in period t when starting at candidates[k]
        self.profiles: tuple[tuple[float, ...], ...] = tuple(self._compute_profile(s) for s in self.candidates)

        # Decision variables: selection weight for each candidate.
        # With favorable problem structure, exactly one will be 1.0 and the rest 0.0.
        # Power limits or coupling can cause fractional solutions without integer mode.
        self.choice_weights = solver.addVariables(
            n_candidates,
            lb=0.0,
            ub=1.0,
            name_prefix=f"{name}_w_",
            out_array=True,
        )

        # Apply integer constraints based on mode
        if integer_mode == IntegerMode.ALL:
            # All candidates are binary
            for i in range(n_candidates):
                solver.changeColIntegrality(self.choice_weights[i].index, HighsVarType.kInteger)
        elif integer_mode == IntegerMode.FIRST and n_candidates > 0:
            # Only first candidate is binary (ensures immediate decision is crisp)
            solver.changeColIntegrality(self.choice_weights[0].index, HighsVarType.kInteger)
        # NONE: all continuous

        # Energy consumed in each period (determined by selection)
        max_energy_per_period = power * max(float(p) for p in self.periods)
        self.energy = solver.addVariables(
            n_periods,
            lb=0.0,
            ub=max_energy_per_period,
            name_prefix=f"{name}_energy_",
            out_array=True,
        )

    def _compute_profile(self, start_time: float) -> tuple[float, ...]:
        """Compute energy profile for a given start time.

        Args:
            start_time: When the load starts (hours from horizon start)

        Returns:
            Tuple of energy consumed in each period (kWh)

        """
        end_time = start_time + self.duration
        profile: list[float] = []

        for t in range(self.n_periods):
            b_start = float(self.boundaries[t])
            b_end = float(self.boundaries[t + 1])

            # Overlap between [start_time, end_time] and [b_start, b_end]
            overlap = max(0.0, min(b_end, end_time) - max(b_start, start_time))
            energy = self.power * overlap
            profile.append(energy)

        return tuple(profile)

    def build_constraints(self) -> None:
        """Build constraints for the schedulable load.

        Constraints:
        1. Exactly one candidate must be selected: sum(w_k) = 1
        2. Energy at each time is determined by selection: E_t = sum(w_k * profile_k[t])

        The constraint matrix has consecutive-ones structure (each candidate affects
        a contiguous set of periods), which often produces integer LP solutions.
        However, power limits or coupling constraints can cause fractional solutions.
        """
        h = self._solver

        # Exactly one start time selected
        self._constraints[SCHEDULABLE_LOAD_CHOICE] = h.addConstr(Highs.qsum(self.choice_weights) == 1.0)

        # Energy at each period equals sum of selected profile contributions
        power_balance_constraints: list[highs_cons] = []
        for t in range(self.n_periods):
            expr = self.energy[t]
            for k, profile in enumerate(self.profiles):
                expr = expr - self.choice_weights[k] * profile[t]
            power_balance_constraints.append(h.addConstr(expr == 0.0))

        self._constraints[SCHEDULABLE_LOAD_POWER_BALANCE] = power_balance_constraints

        # Connection power balance: power = energy / period_length
        h.addConstrs(self.connection_power() * self.periods == -self.energy)

    def cost(self) -> Sequence[highs_linear_expression]:
        """Return the cost expressions of the schedulable load.

        The schedulable load has no inherent cost - costs are applied through
        connections linking the load to the network.
        """
        return []

    def _compute_selected_start_time(self) -> float:
        """Compute the selected start time from choice weights.

        Returns:
            The start time of the selected candidate in hours.

        """
        weights = self.extract_values(self.choice_weights)

        # Find the candidate with the highest weight (should be ~1.0)
        max_weight = 0.0
        selected_start = self.earliest_start

        for k, w in enumerate(weights):
            if w > max_weight:
                max_weight = w
                selected_start = self.candidates[k]

        return selected_start

    def outputs(self) -> Mapping[SchedulableLoadOutputName, OutputData]:
        """Return schedulable load output specifications."""
        # Compute power consumption from energy: power[t] = energy[t] / period[t]
        energy_values = self.extract_values(self.energy)
        power_values = tuple(e / float(p) for e, p in zip(energy_values, self.periods, strict=True))

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
                values=(self._compute_selected_start_time(),),
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
