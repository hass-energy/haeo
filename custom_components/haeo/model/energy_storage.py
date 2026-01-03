"""Energy storage element for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_linear_expression

from .const import OutputType
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence

# Type for energy storage constraint names
type EnergyStorageConstraintName = Literal[
    "energy_storage_power_balance",
    "energy_storage_energy_in_flow",
    "energy_storage_energy_out_flow",
    "energy_storage_soc_max",
    "energy_storage_soc_min",
    "energy_storage_initial_charge",
    "energy_storage_initial_discharge",
]

# Type for all energy storage output names (union of base outputs and constraints)
type EnergyStorageOutputName = (
    Literal[
        "energy_storage_power_charge",
        "energy_storage_power_discharge",
        "energy_storage_energy_stored",
    ]
    | EnergyStorageConstraintName
)

# Energy storage constraint names
ENERGY_STORAGE_CONSTRAINT_NAMES: Final[frozenset[EnergyStorageConstraintName]] = frozenset(
    (
        ENERGY_STORAGE_POWER_BALANCE := "energy_storage_power_balance",
        ENERGY_STORAGE_ENERGY_IN_FLOW := "energy_storage_energy_in_flow",
        ENERGY_STORAGE_ENERGY_OUT_FLOW := "energy_storage_energy_out_flow",
        ENERGY_STORAGE_SOC_MAX := "energy_storage_soc_max",
        ENERGY_STORAGE_SOC_MIN := "energy_storage_soc_min",
        ENERGY_STORAGE_INITIAL_CHARGE := "energy_storage_initial_charge",
        ENERGY_STORAGE_INITIAL_DISCHARGE := "energy_storage_initial_discharge",
    )
)

# Energy storage power constraints
ENERGY_STORAGE_POWER_CONSTRAINTS: Final[frozenset[EnergyStorageConstraintName]] = frozenset(
    (ENERGY_STORAGE_POWER_BALANCE,)
)

# Energy storage output names
ENERGY_STORAGE_OUTPUT_NAMES: Final[frozenset[EnergyStorageOutputName]] = frozenset(
    (
        ENERGY_STORAGE_POWER_CHARGE := "energy_storage_power_charge",
        ENERGY_STORAGE_POWER_DISCHARGE := "energy_storage_power_discharge",
        ENERGY_STORAGE_ENERGY_STORED := "energy_storage_energy_stored",
        *ENERGY_STORAGE_CONSTRAINT_NAMES,
    )
)


class EnergyStorage(Element[EnergyStorageOutputName, EnergyStorageConstraintName]):
    """Energy storage element for electrical system modeling.

    Represents a single logical partition of battery capacity with cumulative energy tracking.
    Battery devices are composed of multiple EnergyStorage partitions connected via
    PartitionBalanceConnection elements that enforce fill ordering.
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
        """Initialize an energy storage element.

        Args:
            name: Name of the energy storage partition
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            capacity: Partition capacity in kWh per period (T+1 values for energy boundaries)
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
        """Build network-dependent constraints for the energy storage partition.

        This includes power balance constraints using connection_power().
        """
        h = self._solver

        # Initial state constraints
        self._constraints[ENERGY_STORAGE_INITIAL_CHARGE] = h.addConstr(self.energy_in[0] == self.initial_charge)
        self._constraints[ENERGY_STORAGE_INITIAL_DISCHARGE] = h.addConstr(self.energy_out[0] == 0.0)

        # Energy flow constraints (cumulative energy can only increase)
        self._constraints[ENERGY_STORAGE_ENERGY_IN_FLOW] = h.addConstrs(self.energy_in[1:] >= self.energy_in[:-1])
        self._constraints[ENERGY_STORAGE_ENERGY_OUT_FLOW] = h.addConstrs(self.energy_out[1:] >= self.energy_out[:-1])

        # SOC constraints (net energy must stay within capacity)
        self._constraints[ENERGY_STORAGE_SOC_MAX] = h.addConstrs(self.stored_energy[1:] <= self.capacity[1:])
        self._constraints[ENERGY_STORAGE_SOC_MIN] = h.addConstrs(self.stored_energy[1:] >= 0)

        # Power balance: connection_power equals net partition power
        self._constraints[ENERGY_STORAGE_POWER_BALANCE] = h.addConstrs(
            self.connection_power() == self.power_consumption - self.power_production
        )

    def cost(self) -> Sequence[highs_linear_expression]:
        """Return the cost expressions of the energy storage partition."""
        return []

    def outputs(self) -> Mapping[EnergyStorageOutputName, OutputData]:
        """Return energy storage partition output specifications."""
        outputs: dict[EnergyStorageOutputName, OutputData] = {
            ENERGY_STORAGE_POWER_CHARGE: OutputData(
                type=OutputType.POWER,
                unit="kW",
                values=self.extract_values(self.power_consumption),
                direction="-",
            ),
            ENERGY_STORAGE_POWER_DISCHARGE: OutputData(
                type=OutputType.POWER,
                unit="kW",
                values=self.extract_values(self.power_production),
                direction="+",
            ),
            ENERGY_STORAGE_ENERGY_STORED: OutputData(
                type=OutputType.ENERGY,
                unit="kWh",
                values=self.extract_values(self.stored_energy),
            ),
        }

        # Add constraint shadow prices
        for constraint_name in self._constraints:
            # Skip initial state constraints (internal implementation details)
            if constraint_name in (ENERGY_STORAGE_INITIAL_CHARGE, ENERGY_STORAGE_INITIAL_DISCHARGE):
                continue

            unit = "$/kW" if constraint_name in ENERGY_STORAGE_POWER_CONSTRAINTS else "$/kWh"
            outputs[constraint_name] = OutputData(
                type=OutputType.SHADOW_PRICE,
                unit=unit,
                values=self.extract_values(self._constraints[constraint_name]),
            )

        return outputs
