"""Battery balance connection for energy redistribution between battery sections."""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from .const import OUTPUT_TYPE_POWER_FLOW
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence

if TYPE_CHECKING:
    from .battery import Battery

# Type for constraint names
type BatteryBalanceConnectionConstraintName = Literal[
    "balance_min_transfer_down",
    "balance_fill_lower_capacity",
]

# Type for output names
type BatteryBalanceConnectionOutputName = (
    Literal[
        "balance_power_down",
        "balance_power_up",
    ]
    | BatteryBalanceConnectionConstraintName
)

BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES: Final[frozenset[BatteryBalanceConnectionOutputName]] = frozenset(
    (
        BALANCE_POWER_DOWN := "balance_power_down",
        BALANCE_POWER_UP := "balance_power_up",
        # Constraints
        BALANCE_MIN_TRANSFER_DOWN := "balance_min_transfer_down",
        BALANCE_FILL_LOWER_CAPACITY := "balance_fill_lower_capacity",
    )
)


class BatteryBalanceConnection(Element[BatteryBalanceConnectionOutputName, BatteryBalanceConnectionConstraintName]):
    """Battery balance connection for energy redistribution between adjacent battery sections.

    This element enforces proper energy flow between battery sections when capacities
    change dynamically. It operates on T periods to integrate with battery power balance.

    Upward transfer (lower → upper): Bookkeeping transfer forced by capacity shrinkage.
    When lower section's capacity shrinks, energy above new capacity must move up.
    This is a constant value computed from capacity changes, not a decision variable.

    Downward transfer (upper → lower): Balancing flow to fill lower section's available
    capacity. This is a slack variable constrained to be at least as large as upward
    transfer, ensuring energy pushed up is returned if the lower section has capacity.

    The constraints work together:
    1. power_up is fixed to capacity shrinkage (forced bookkeeping transfer)
    2. power_down >= power_up (must compensate bookkeeping)
    3. power_down * period >= capacity_lower - stored_energy (fill available capacity)

    The lower section's capacity constraint prevents overfilling.
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
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            upper: Name of the upper battery section (receives upward transfer)
            lower: Name of the lower battery section (receives downward transfer)
            capacity_lower: Lower section capacity in kWh (T+1 fence-posted values)

        """
        super().__init__(name=name, periods=periods, solver=solver)
        n_periods = self.n_periods
        h = solver

        # Store element names for lookup during constraint building
        self.upper = upper
        self.lower = lower

        # Broadcast capacity to T+1 (energy boundaries)
        self.capacity_lower = broadcast_to_sequence(capacity_lower, n_periods + 1)

        # Compute capacity shrinkage: max(0, capacity[t] - capacity[t+1])
        capacity_delta = np.maximum(0, self.capacity_lower[:-1] - self.capacity_lower[1:])
        self.capacity_shrinkage: NDArray[np.floating] = capacity_delta

        # Upward power = shrinkage energy / period duration (constant, not variable)
        self.power_up: NDArray[np.floating] = self.capacity_shrinkage / self.periods

        # Create downward transfer variable (slack, >= 0)
        self.power_down = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_power_down_", out_array=True)

        # Store battery references (set during registration in network.add)
        self._upper_battery: Battery | None = None
        self._lower_battery: Battery | None = None

    def set_battery_references(self, upper_battery: "Battery", lower_battery: "Battery") -> None:
        """Set references to the connected battery sections.

        Called by Network.add() after looking up battery elements by name.

        Args:
            upper_battery: The upper battery section element
            lower_battery: The lower battery section element

        """
        self._upper_battery = upper_battery
        self._lower_battery = lower_battery

        # Register this balance connection with both batteries
        # Upper battery: downward is outgoing (source), upward is incoming (target)
        upper_battery.register_connection(self, "source")
        # Lower battery: downward is incoming (target), upward is outgoing (source)
        lower_battery.register_connection(self, "target")

    @property
    def power_source_target(self) -> HighspyArray:
        """Power flowing from source (upper) to target (lower).

        This is the downward transfer variable.
        """
        return self.power_down

    @property
    def power_target_source(self) -> NDArray[np.floating]:
        """Power flowing from target (lower) to source (upper).

        This is the upward transfer, a constant computed from capacity shrinkage.
        """
        return self.power_up

    @property
    def efficiency_source_target(self) -> NDArray[np.floating]:
        """Efficiency for source to target (downward) transfer.

        Balance transfers are lossless (100% efficiency).
        """
        return np.ones(self.n_periods)

    @property
    def efficiency_target_source(self) -> NDArray[np.floating]:
        """Efficiency for target to source (upward) transfer.

        Balance transfers are lossless (100% efficiency).
        """
        return np.ones(self.n_periods)

    def build_constraints(self) -> None:
        """Build constraints for the battery balance connection.

        Constraints:
        1. power_down >= power_up (compensate upward bookkeeping transfer)
        2. power_down * period >= capacity_lower[t+1] - stored_energy[t+1] (fill capacity)
        """
        h = self._solver

        if self._lower_battery is None:
            msg = f"Lower battery reference not set for {self.name}"
            raise ValueError(msg)

        # Constraint 1: Downward transfer must at least compensate upward bookkeeping
        # This ensures any energy pushed up by capacity shrinkage flows back down
        self._constraints[BALANCE_MIN_TRANSFER_DOWN] = h.addConstrs(self.power_down >= self.power_up)

        # Constraint 2: Downward energy must fill lower section's available capacity
        # The lower section's SOC max constraint prevents overfilling
        energy_down = self.power_down * self.periods
        available_capacity = self.capacity_lower[1:] - self._lower_battery.stored_energy[1:]
        self._constraints[BALANCE_FILL_LOWER_CAPACITY] = h.addConstrs(energy_down >= available_capacity)

    def cost(self) -> Sequence[highs_linear_expression]:
        """Return the cost expressions of the balance connection.

        Balance transfers are cost-free (transparent redistribution).
        """
        return []

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
                values=tuple(self.power_up.tolist()),
                direction="-",
            ),
        }

        # Add constraint shadow prices
        for constraint_name in self._constraints:
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_POWER_FLOW,  # Shadow prices
                unit="$/kW",
                values=self.extract_values(self._constraints[constraint_name]),
            )

        return outputs
