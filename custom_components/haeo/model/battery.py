"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_linear_expression

from .const import OUTPUT_TYPE_ENERGY, OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence

# Type for battery constraint names
type BatteryConstraintName = Literal[
    "battery_power_balance",
    "battery_energy_in_flow",
    "battery_energy_out_flow",
    "battery_soc_max",
    "battery_soc_min",
    "battery_initial_charge",
    "battery_initial_discharge",
]

# Type for all battery output names (union of base outputs and constraints)
type BatteryOutputName = (
    Literal[
        "battery_power_charge",
        "battery_power_discharge",
        "battery_energy_stored",
    ]
    | BatteryConstraintName
)

# Battery constraint names
BATTERY_CONSTRAINT_NAMES: Final[frozenset[BatteryConstraintName]] = frozenset(
    (
        BATTERY_POWER_BALANCE := "battery_power_balance",
        BATTERY_ENERGY_IN_FLOW := "battery_energy_in_flow",
        BATTERY_ENERGY_OUT_FLOW := "battery_energy_out_flow",
        BATTERY_SOC_MAX := "battery_soc_max",
        BATTERY_SOC_MIN := "battery_soc_min",
        BATTERY_INITIAL_CHARGE := "battery_initial_charge",
        BATTERY_INITIAL_DISCHARGE := "battery_initial_discharge",
    )
)

# Battery power constraints
BATTERY_POWER_CONSTRAINTS: Final[frozenset[BatteryConstraintName]] = frozenset((BATTERY_POWER_BALANCE,))

# Battery output names
BATTERY_OUTPUT_NAMES: Final[frozenset[BatteryOutputName]] = frozenset(
    (
        BATTERY_POWER_CHARGE := "battery_power_charge",
        BATTERY_POWER_DISCHARGE := "battery_power_discharge",
        BATTERY_ENERGY_STORED := "battery_energy_stored",
        *BATTERY_CONSTRAINT_NAMES,
    )
)


class Battery(Element[BatteryOutputName, BatteryConstraintName]):
    """Battery entity for electrical system modeling.

    Represents a single battery section with cumulative energy tracking.
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        capacity: Sequence[float] | float,
        initial_charge: float,
    ) -> None:
        """Initialize a battery entity.

        Args:
            name: Name of the battery
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            capacity: Battery capacity in kWh per period (T+1 values for energy boundaries)
            initial_charge: Initial charge in kWh

        """
        super().__init__(name=name, periods=periods, solver=solver)
        n_periods = self.n_periods

        # Broadcast capacity to n_periods + 1 (energy boundaries)
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)

        # Store initial charge for constraint
        self.initial_charge = initial_charge

        # Create all energy variables (including initial state at t=0)
        self.energy_in = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_energy_in_", out_array=True)
        self.energy_out = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_energy_out_", out_array=True)

        # Pre-calculate power and energy expressions
        self.power_consumption = (self.energy_in[1:] - self.energy_in[:-1]) * (1.0 / self.periods)
        self.power_production = (self.energy_out[1:] - self.energy_out[:-1]) * (1.0 / self.periods)
        self.stored_energy = self.energy_in - self.energy_out

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        """
        h = self._solver

        # Initial state constraints
        self._constraints[BATTERY_INITIAL_CHARGE] = h.addConstr(self.energy_in[0] == self.initial_charge)
        self._constraints[BATTERY_INITIAL_DISCHARGE] = h.addConstr(self.energy_out[0] == 0.0)

        # Energy flow constraints (cumulative energy can only increase)
        self._constraints[BATTERY_ENERGY_IN_FLOW] = h.addConstrs(self.energy_in[1:] >= self.energy_in[:-1])
        self._constraints[BATTERY_ENERGY_OUT_FLOW] = h.addConstrs(self.energy_out[1:] >= self.energy_out[:-1])

        # SOC constraints (net energy must stay within capacity)
        self._constraints[BATTERY_SOC_MAX] = h.addConstrs(self.stored_energy[1:] <= self.capacity[1:])
        self._constraints[BATTERY_SOC_MIN] = h.addConstrs(self.stored_energy[1:] >= 0)

        # Power balance: connection_power equals net battery power
        self._constraints[BATTERY_POWER_BALANCE] = h.addConstrs(
            self.connection_power() == self.power_consumption - self.power_production
        )

    def cost(self) -> Sequence[highs_linear_expression]:
        """Return the cost expressions of the battery."""
        return []

    def outputs(self) -> Mapping[BatteryOutputName, OutputData]:
        """Return battery output specifications."""
        outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_POWER_CHARGE: OutputData(
                type=OUTPUT_TYPE_POWER,
                unit="kW",
                values=self.extract_values(self.power_consumption),
                direction="-",
            ),
            BATTERY_POWER_DISCHARGE: OutputData(
                type=OUTPUT_TYPE_POWER,
                unit="kW",
                values=self.extract_values(self.power_production),
                direction="+",
            ),
            BATTERY_ENERGY_STORED: OutputData(
                type=OUTPUT_TYPE_ENERGY,
                unit="kWh",
                values=self.extract_values(self.stored_energy),
            ),
        }

        # Add constraint shadow prices
        for constraint_name in self._constraints:
            # Skip initial state constraints (internal implementation details)
            if constraint_name in (BATTERY_INITIAL_CHARGE, BATTERY_INITIAL_DISCHARGE):
                continue

            unit = "$/kW" if constraint_name in BATTERY_POWER_CONSTRAINTS else "$/kWh"
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit=unit,
                values=self.extract_values(self._constraints[constraint_name]),
            )

        return outputs
