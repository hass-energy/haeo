"""Battery balance connection for energy redistribution between battery sections."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray

from .const import OUTPUT_TYPE_POWER_FLOW
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence

if TYPE_CHECKING:
    from .battery import Battery

type BatteryBalanceConnectionConstraintName = Literal[
    "balance_down_demand",
    "balance_down_available",
    "balance_down_slack_min",
    "balance_up_excess",
    "balance_up_slack_min",
    "balance_up_max",
]

type BatteryBalanceConnectionOutputName = (
    Literal[
        "balance_power_down",
        "balance_power_up",
        "balance_slack_down",
        "balance_slack_up",
    ]
    | BatteryBalanceConnectionConstraintName
)

BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES: Final[frozenset[BatteryBalanceConnectionOutputName]] = frozenset(
    (
        BALANCE_POWER_DOWN := "balance_power_down",
        BALANCE_POWER_UP := "balance_power_up",
        BALANCE_SLACK_DOWN := "balance_slack_down",
        BALANCE_SLACK_UP := "balance_slack_up",
        BALANCE_DOWN_DEMAND := "balance_down_demand",
        BALANCE_DOWN_AVAILABLE := "balance_down_available",
        BALANCE_DOWN_SLACK_MIN := "balance_down_slack_min",
        BALANCE_UP_EXCESS := "balance_up_excess",
        BALANCE_UP_SLACK_MIN := "balance_up_slack_min",
        BALANCE_UP_MAX := "balance_up_max",
    )
)


class BatteryBalanceConnection(Element[BatteryBalanceConnectionOutputName, BatteryBalanceConnectionConstraintName]):
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

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        upper: str,
        lower: str,
        capacity_lower: Sequence[float] | float,
    ) -> None:
        """Initialize a battery balance connection.

        Args:
            name: Name of the balance connection
            periods: Period durations in hours
            solver: HiGHS solver instance
            upper: Name of upper battery section (receives upward transfer)
            lower: Name of lower battery section (receives downward transfer)
            capacity_lower: Lower section capacity in kWh (T+1 fence-posted values)

        """
        super().__init__(name=name, periods=periods, solver=solver)
        n_periods = self.n_periods
        h = solver

        self.upper = upper
        self.lower = lower
        self.capacity_lower = broadcast_to_sequence(capacity_lower, n_periods + 1)

        self.power_down = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_power_down_", out_array=True)
        self.power_up = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_power_up_", out_array=True)
        self.slack_down = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_slack_down_", out_array=True)
        self.slack_up = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_slack_up_", out_array=True)

        self._upper_battery: Battery | None = None
        self._lower_battery: Battery | None = None

    def set_battery_references(self, upper_battery: "Battery", lower_battery: "Battery") -> None:
        """Set references to connected battery sections. Called by Network.add()."""
        self._upper_battery = upper_battery
        self._lower_battery = lower_battery
        upper_battery.register_connection(self, "source")
        lower_battery.register_connection(self, "target")

    @property
    def power_source_target(self) -> HighspyArray:
        """Power flowing from source (upper) to target (lower)."""
        return self.power_down

    @property
    def power_target_source(self) -> HighspyArray:
        """Power flowing from target (lower) to source (upper)."""
        return self.power_up

    @property
    def efficiency_source_target(self) -> NDArray[np.floating]:
        """Efficiency for downward transfer. Balance transfers are lossless."""
        return np.ones(self.n_periods)

    @property
    def efficiency_target_source(self) -> NDArray[np.floating]:
        """Efficiency for upward transfer. Balance transfers are lossless."""
        return np.ones(self.n_periods)

    def build_constraints(self) -> None:
        """Build constraints for the battery balance connection.

        Downward flow implements P_down = min(demand, E_upper):
            P_down + S_down = demand
            P_down <= E_upper
            S_down >= demand - E_upper

        Upward flow implements P_up = max(0, excess):
            P_up - S_up = excess
            S_up >= -excess

        Battery SOC constraints (E >= 0, E <= C) fully bind these to unique values.
        When excess > 0, lower's capacity constraint forces P_up = excess.
        When excess <= 0, the slack absorbs the negative and P_up = 0.
        """

        h = self._solver

        # Power down must be at least the amount of energy needed in the lower battery or the amount available in the upper battery.
        # The goal of this constraint is to force energy transfer down to the lowest section possible.
        # Given that the amount of energy in the upper battery is always >= 0 this also ensures that it is positive
        #
        # Thus the constraint is:
        #
        #  power_down >= min(energy_missing_in_lower, energy_available_in_upper)
        #
        # This can be implemented using a single slack variable S_down
        #
        # The resulting power transfer is in theory unbounded above at this point, however however the battery SOC constraints fix it to a single value
        # Consider the two cases:
        # 1. energy_missing_in_lower <= energy_available_in_upper
        #    In this case if we tried to move more than energy_missing_in_lower into the lower battery it would exceed its capacity, which is forbidden by the battery SOC constraints
        #    Thus the battery SOC constraints force power_down == energy_missing_in_lower
        # 2. energy_missing_in_lower > energy_available_in_upper
        #    In this case if we tried to move more than energy_available_in_upper out of the upper battery it would go negative, which is forbidden by the battery SOC constraints
        #    Thus the battery SOC constraints force power_down == energy_available_in_upper
        #
        # Power up is used as a relief valve so that if there is excess energy in the lower battery due to changing capacity it can be moved up to the upper battery without cost penalty.
        # Power up must be no more than how much the lower battery is about to exceed its capacity by\
        #
        # Thus the constraint is:
        #
        # 0 <= power_up <= max(0, current_energy - next_capacity)
        #
        # This can also be implemented using a single slack variable S_up
        # The battery SOC constraints then fully bind power_up to a single value
        # The only non trivial case here is when next_capacity has shrunk, otherwise current_energy would never exceed next_capacity due to the battery SOC constraints
        # So when it does shrink then the max(0, current_energy - next_capacity) can be positive.
        # In that case though, the amount it is positive is exactly how much energy needs to be moved up to the upper battery to prevent the lower battery from exceeding its capacity
        # Therefore the battery SOC constraints force power_up == current_energy - next_capacity giving only a single feasible value

        if self._lower_battery is None or self._upper_battery is None:
            msg = f"Battery references not set for {self.name}"
            raise ValueError(msg)

        lower_stored = self._lower_battery.stored_energy
        upper_stored = self._upper_battery.stored_energy
        capacity_lower = np.array(self.capacity_lower)
        periods = self.periods

        energy_down = self.power_down * periods
        energy_up = self.power_up * periods
        slack_energy_down = self.slack_down * periods
        slack_energy_up = self.slack_up * periods

        demand = capacity_lower[:-1] - lower_stored[:-1]
        excess = lower_stored[:-1] - capacity_lower[1:]

        # Downward: P_down = min(demand, E_upper)
        self._constraints[BALANCE_DOWN_DEMAND] = h.addConstrs(energy_down + slack_energy_down == demand)
        self._constraints[BALANCE_DOWN_AVAILABLE] = h.addConstrs(energy_down <= upper_stored[:-1])
        self._constraints[BALANCE_DOWN_SLACK_MIN] = h.addConstrs(slack_energy_down >= demand - upper_stored[:-1])

        # Upward: 0 <= P_up <= max(0, excess)
        # Lower bound via equality: P_up = excess + S_up with S_up >= max(0, -excess)
        # Upper bound: P_up <= excess + S_max with S_max >= max(0, -excess)
        # Battery SOC constraints then force P_up = max(0, excess) exactly.
        self._constraints[BALANCE_UP_EXCESS] = h.addConstrs(energy_up - slack_energy_up == excess)
        self._constraints[BALANCE_UP_SLACK_MIN] = h.addConstrs(slack_energy_up >= -excess)

        # Upper bound on P_up
        slack_energy_up_max = self.slack_up_max * periods
        self._constraints[BALANCE_UP_MAX] = h.addConstrs(energy_up <= excess + slack_energy_up_max)
        h.addConstrs(slack_energy_up_max >= -excess)

    def outputs(self) -> Mapping[BatteryBalanceConnectionOutputName, OutputData]:
        """Return output specifications for the balance connection."""
        outputs: dict[BatteryBalanceConnectionOutputName, OutputData] = {
            BALANCE_POWER_DOWN: OutputData(
                type=OUTPUT_TYPE_POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.power_down),
                direction="+",
            ),
            BALANCE_POWER_UP: OutputData(
                type=OUTPUT_TYPE_POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.power_up),
                direction="-",
            ),
            BALANCE_SLACK_DOWN: OutputData(
                type=OUTPUT_TYPE_POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.slack_down),
            ),
            BALANCE_SLACK_UP: OutputData(
                type=OUTPUT_TYPE_POWER_FLOW,
                unit="kW",
                values=self.extract_values(self.slack_up),
            ),
        }

        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_POWER_FLOW,
                unit="$/kW",
                values=self.extract_values(self._constraints[constraint_name]),
            )

        return outputs
