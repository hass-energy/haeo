"""Battery balance connection for energy redistribution between battery sections."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_cons, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .connection import Connection
from .const import OutputType
from .output_data import OutputData
from .reactive import TrackedParam, constraint, cost
from .util import broadcast_to_sequence

# Model element type for battery balance connections
ELEMENT_TYPE: Final = "battery_balance_connection"

if TYPE_CHECKING:
    from .battery import Battery

type BatteryBalanceConnectionConstraintName = Literal[
    "balance_down_lower_bound",
    "balance_down_slack_bound",
    "balance_up_upper_bound",
    "balance_up_slack_bound",
]

type BatteryBalanceConnectionOutputName = (
    Literal[
        "balance_power_down",
        "balance_power_up",
        "balance_unmet_demand",
        "balance_absorbed_excess",
    ]
    | BatteryBalanceConnectionConstraintName
)

BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES: Final[frozenset[BatteryBalanceConnectionOutputName]] = frozenset(
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


class BatteryBalanceConnection(Connection[BatteryBalanceConnectionOutputName]):
    """Lossless energy redistribution between adjacent battery sections.

    Enforces ordering (lower fills before upper) and handles capacity changes
    through bidirectional power flow. Battery SOC constraints fully bind the
    flow values—this element sets up the feasibility region.

    Downward (upper → lower): P_down = min(demand, E_upper)
    Upward (lower → upper): P_up = max(0, excess)

    Where:
        demand = C_lower - E_lower (room in lower section)
        excess = E_lower - C_new (energy above new capacity)
    """

    # Default penalty for slack variables in $/kWh
    # Must be larger than any reasonable energy price to ensure slacks are minimized
    DEFAULT_SLACK_PENALTY: Final[float] = 100.0

    # Parameters
    capacity_lower: TrackedParam[NDArray[np.float64]] = TrackedParam()

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
        """Initialize a battery balance connection.

        Args:
            name: Name of the balance connection
            periods: Period durations in hours
            solver: HiGHS solver instance
            upper: Name of upper battery section (receives upward transfer)
            lower: Name of lower battery section (receives downward transfer)
            capacity_lower: Lower section capacity in kWh (T+1 fence-posted values)
            slack_penalty: Penalty in $/kWh for slack variables (default: 1.0).
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

        self._upper_battery: Battery | None = None
        self._lower_battery: Battery | None = None

    def set_battery_references(self, upper_battery: "Battery", lower_battery: "Battery") -> None:
        """Set references to connected battery sections. Called by Network.add()."""
        self._upper_battery = upper_battery
        self._lower_battery = lower_battery
        upper_battery.register_connection(self, "source")
        lower_battery.register_connection(self, "target")

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

    @constraint
    def down_lower_bound_constraint(self) -> list[highs_cons]:
        """Constraint: energy_down >= demand - unmet_demand."""
        if self._lower_battery is None or self._upper_battery is None:
            msg = f"Battery references not set for {self.name}"
            raise ValueError(msg)

        lower_stored = self._lower_battery.stored_energy
        capacity_lower = np.array(self.capacity_lower)
        periods = self.periods

        energy_down = self._power_down * periods
        unmet_demand_energy = self.unmet_demand * periods

        # demand = room in lower section = capacity - current energy
        demand = capacity_lower[:-1] - lower_stored[:-1]

        return self._solver.addConstrs(energy_down >= demand - unmet_demand_energy)

    @constraint
    def down_slack_bound_constraint(self) -> list[highs_cons]:
        """Constraint: unmet_demand >= demand - available."""
        if self._lower_battery is None or self._upper_battery is None:
            msg = f"Battery references not set for {self.name}"
            raise ValueError(msg)

        lower_stored = self._lower_battery.stored_energy
        upper_stored = self._upper_battery.stored_energy
        capacity_lower = np.array(self.capacity_lower)
        periods = self.periods

        unmet_demand_energy = self.unmet_demand * periods

        # demand = room in lower section = capacity - current energy
        demand = capacity_lower[:-1] - lower_stored[:-1]
        # available = energy in upper section
        available = upper_stored[:-1]

        return self._solver.addConstrs(unmet_demand_energy >= demand - available)

    @constraint
    def up_upper_bound_constraint(self) -> list[highs_cons]:
        """Constraint: energy_up <= excess + absorbed_excess."""
        if self._lower_battery is None or self._upper_battery is None:
            msg = f"Battery references not set for {self.name}"
            raise ValueError(msg)

        lower_stored = self._lower_battery.stored_energy
        capacity_lower = np.array(self.capacity_lower)
        periods = self.periods

        energy_up = self._power_up * periods
        absorbed_excess_energy = self.absorbed_excess * periods

        # excess = current energy - next capacity (positive when capacity shrinks)
        excess = lower_stored[:-1] - capacity_lower[1:]

        return self._solver.addConstrs(energy_up <= excess + absorbed_excess_energy)

    @constraint
    def up_slack_bound_constraint(self) -> list[highs_cons]:
        """Constraint: absorbed_excess >= -excess."""
        if self._lower_battery is None or self._upper_battery is None:
            msg = f"Battery references not set for {self.name}"
            raise ValueError(msg)

        lower_stored = self._lower_battery.stored_energy
        capacity_lower = np.array(self.capacity_lower)
        periods = self.periods

        absorbed_excess_energy = self.absorbed_excess * periods

        # excess = current energy - next capacity (positive when capacity shrinks)
        excess = lower_stored[:-1] - capacity_lower[1:]

        return self._solver.addConstrs(absorbed_excess_energy >= -excess)

    @cost
    def slack_penalty_cost(self) -> list[highs_linear_expression]:
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

    def outputs(self) -> Mapping[BatteryBalanceConnectionOutputName, OutputData]:
        """Return output specifications for the balance connection."""
        outputs: dict[BatteryBalanceConnectionOutputName, OutputData] = {
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

        constraint_mapping: dict[str, BatteryBalanceConnectionConstraintName] = {
            "down_lower_bound_constraint": BALANCE_DOWN_LOWER_BOUND,
            "down_slack_bound_constraint": BALANCE_DOWN_SLACK_BOUND,
            "up_upper_bound_constraint": BALANCE_UP_UPPER_BOUND,
            "up_slack_bound_constraint": BALANCE_UP_SLACK_BOUND,
        }

        for method_name, output_name in constraint_mapping.items():
            if method_name in self._applied_constraints:
                outputs[output_name] = OutputData(
                    type=OutputType.POWER_FLOW,
                    unit="$/kW",
                    values=self.extract_values(self._applied_constraints[method_name]),
                )

        return outputs
