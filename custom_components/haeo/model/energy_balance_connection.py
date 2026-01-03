"""Energy balance connection for energy redistribution between energy storage partitions."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np

from .connection import Connection
from .const import OutputType
from .output_data import OutputData
from .util import broadcast_to_sequence

# Model element type for energy balance connections
ELEMENT_TYPE: Final = "energy_balance_connection"

if TYPE_CHECKING:
    from .energy_storage import EnergyStorage

type EnergyBalanceConnectionConstraintName = Literal[
    "balance_down_lower_bound",
    "balance_down_slack_bound",
    "balance_up_upper_bound",
    "balance_up_slack_bound",
]

type EnergyBalanceConnectionOutputName = (
    Literal[
        "balance_power_down",
        "balance_power_up",
        "balance_unmet_demand",
        "balance_absorbed_excess",
    ]
    | EnergyBalanceConnectionConstraintName
)

ENERGY_BALANCE_CONNECTION_OUTPUT_NAMES: Final[frozenset[EnergyBalanceConnectionOutputName]] = frozenset(
    (
        BALANCE_POWER_DOWN := "balance_power_down",
        BALANCE_POWER_UP := "balance_power_up",
        BALANCE_UNMET_DEMAND := "balance_unmet_demand",
        BALANCE_ABSORBED_EXCESS := "balance_absorbed_excess",
        BALANCE_DOWN_LOWER_BOUND := "balance_down_lower_bound",
        BALANCE_DOWN_SLACK_BOUND := "balance_down_slack_bound",
        BALANCE_UP_UPPER_BOUND := "balance_up_upper_bound",
        BALANCE_UP_SLACK_BOUND := "balance_up_slack_bound",
    )
)


class EnergyBalanceConnection(Connection[EnergyBalanceConnectionOutputName, EnergyBalanceConnectionConstraintName]):
    """Lossless energy redistribution between adjacent energy storage partitions.

    Enforces ordering (lower fills before upper) and handles capacity changes
    through bidirectional power flow. Partition SOC constraints fully bind the
    flow values—this element sets up the feasibility region.

    Downward (upper → lower): P_down = min(demand, E_upper)
    Upward (lower → upper): P_up = max(0, excess)

    Where:
        demand = C_lower - E_lower (room in lower partition)
        excess = E_lower - C_new (energy above new capacity)
    """

    # Default penalty for slack variables in $/kWh
    # Must be larger than any reasonable energy price to ensure slacks are minimized
    DEFAULT_SLACK_PENALTY: Final[float] = 100.0

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        upper: str,
        lower: str,
        capacity_lower: Sequence[float] | float,
        slack_penalty: float | None = None,
    ) -> None:
        """Initialize an energy balance connection.

        Args:
            name: Name of the balance connection
            periods: Period durations in hours
            solver: HiGHS solver instance
            upper: Name of upper energy storage partition (receives upward transfer)
            lower: Name of lower energy storage partition (receives downward transfer)
            capacity_lower: Lower partition capacity in kWh (T+1 fence-posted values)
            slack_penalty: Penalty in $/kWh for slack variables (default: 100.0).
                Must be larger than typical energy prices to ensure min/max
                constraints are enforced correctly.

        """
        super().__init__(name=name, periods=periods, solver=solver, source=upper, target=lower)
        n_periods = self.n_periods
        h = solver

        self.capacity_lower = broadcast_to_sequence(capacity_lower, n_periods + 1)
        self._slack_penalty = slack_penalty if slack_penalty is not None else self.DEFAULT_SLACK_PENALTY

        self._power_down = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_power_down_", out_array=True)
        self._power_up = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_power_up_", out_array=True)
        self.unmet_demand = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_unmet_demand_", out_array=True)
        self.absorbed_excess = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_absorbed_excess_", out_array=True)

        self._upper_partition: EnergyStorage | None = None
        self._lower_partition: EnergyStorage | None = None

    def set_partition_references(self, upper_partition: "EnergyStorage", lower_partition: "EnergyStorage") -> None:
        """Set references to connected energy storage partitions. Called by Network.add()."""
        self._upper_partition = upper_partition
        self._lower_partition = lower_partition
        upper_partition.register_connection(self, "source")
        lower_partition.register_connection(self, "target")

    @property
    def power_into_source(self) -> HighspyArray:
        """Return effective power flowing into the source (upper) element.

        Power flowing up from lower (positive) minus power flowing down to lower (negative).
        Balance transfers are lossless.
        """
        return self._power_up - self._power_down

    @property
    def power_into_target(self) -> HighspyArray:
        """Return effective power flowing into the target (lower) element.

        Power flowing down from upper (positive) minus power flowing up to upper (negative).
        Balance transfers are lossless.
        """
        return self._power_down - self._power_up

    def build_constraints(self) -> None:
        """Build constraints for the energy balance connection.

        Downward flow implements energy_down >= min(demand, available):
            energy_down >= demand - unmet_demand
            unmet_demand >= demand - available
            unmet_demand >= 0 (variable bound)
            energy_down >= 0 (variable bound)

        When demand <= available: unmet_demand lower bound is negative (demand - available < 0),
        so unmet_demand = 0 and energy_down >= demand.
        When demand > available: unmet_demand >= demand - available,
        so energy_down >= available.

        The min() behavior requires the cost() penalty on unmet_demand to push it
        to its minimum value; without an objective term, the solver could set
        unmet_demand arbitrarily high.

        Upward flow implements 0 <= energy_up <= max(0, excess):
            energy_up <= excess + absorbed_excess
            absorbed_excess >= -excess
            absorbed_excess >= 0 (variable bound)
            energy_up >= 0 (variable bound)

        When excess <= 0: absorbed_excess >= -excess (positive) absorbs the negative,
        so energy_up <= 0, combined with energy_up >= 0 gives energy_up = 0.
        When excess > 0: absorbed_excess = 0, so energy_up <= excess.

        The max() behavior requires the cost() penalty on absorbed_excess to push
        it to its minimum value.
        """
        h = self._solver

        if self._lower_partition is None or self._upper_partition is None:
            msg = f"Partition references not set for {self.name}"
            raise ValueError(msg)

        lower_stored = self._lower_partition.stored_energy
        upper_stored = self._upper_partition.stored_energy
        capacity_lower = np.array(self.capacity_lower)
        periods = self.periods

        energy_down = self._power_down * periods
        energy_up = self._power_up * periods
        unmet_demand_energy = self.unmet_demand * periods
        absorbed_excess_energy = self.absorbed_excess * periods

        # demand = room in lower partition = capacity - current energy
        demand = capacity_lower[:-1] - lower_stored[:-1]
        # available = energy in upper partition
        available = upper_stored[:-1]
        # excess = current energy - next capacity (positive when capacity shrinks)
        excess = lower_stored[:-1] - capacity_lower[1:]

        # Downward flow constraint: energy_down >= min(demand, available)
        # Lower bound constraint - SOC constraints provide upper bound
        self._constraints[BALANCE_DOWN_LOWER_BOUND] = h.addConstrs(energy_down >= demand - unmet_demand_energy)
        self._constraints[BALANCE_DOWN_SLACK_BOUND] = h.addConstrs(unmet_demand_energy >= demand - available)

        # Upward flow constraint: 0 <= energy_up <= max(0, excess)
        # Upper bound constraint - SOC constraints force equality when excess > 0
        self._constraints[BALANCE_UP_UPPER_BOUND] = h.addConstrs(energy_up <= excess + absorbed_excess_energy)
        self._constraints[BALANCE_UP_SLACK_BOUND] = h.addConstrs(absorbed_excess_energy >= -excess)

    def cost(self) -> Sequence[highs_linear_expression]:
        """Return cost expressions penalizing slack variables.

        The slack variables allow min/max constraints to be implemented in LP form.
        Without penalties, the solver could set slack arbitrarily, breaking the
        intended behavior:
        - unmet_demand slack: minimizing achieves power_down >= min(demand, available)
        - absorbed_excess slack: minimizing achieves power_up <= max(0, excess)

        The penalty must be larger than typical energy prices to ensure slacks are
        minimized regardless of other optimization objectives.
        """
        periods = self.periods

        # Penalize both slack variables
        unmet_cost = self.unmet_demand * periods * self._slack_penalty
        absorbed_cost = self.absorbed_excess * periods * self._slack_penalty

        return [*list(unmet_cost), *list(absorbed_cost)]

    def outputs(self) -> Mapping[EnergyBalanceConnectionOutputName, OutputData]:
        """Return output specifications for the balance connection."""
        outputs: dict[EnergyBalanceConnectionOutputName, OutputData] = {
            BALANCE_POWER_DOWN: OutputData(
                type=OutputType.POWER_FLOW,
                unit="kW",
                values=self.extract_values(self._power_down),
                direction="+",
            ),
            BALANCE_POWER_UP: OutputData(
                type=OutputType.POWER_FLOW,
                unit="kW",
                values=self.extract_values(self._power_up),
                direction="-",
            ),
            BALANCE_UNMET_DEMAND: OutputData(
                type=OutputType.POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.unmet_demand),
            ),
            BALANCE_ABSORBED_EXCESS: OutputData(
                type=OutputType.POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.absorbed_excess),
            ),
        }

        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OutputType.POWER_FLOW,
                unit="$/kW",
                values=self.extract_values(self._constraints[constraint_name]),
            )

        return outputs
