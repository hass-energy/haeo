"""Energy storage element for electrical system modeling."""

from collections.abc import Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import TrackedParam, constraint, output
from custom_components.haeo.model.util import broadcast_to_sequence

# Type for energy storage constraint names (shadow prices exposed as outputs)
type EnergyStorageConstraintName = Literal[
    "energy_storage_power_balance",
    "energy_storage_energy_in_flow",
    "energy_storage_energy_out_flow",
    "energy_storage_soc_max",
    "energy_storage_soc_min",
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

# All energy storage output names (includes constraint shadow prices)
ENERGY_STORAGE_OUTPUT_NAMES: Final[frozenset[EnergyStorageOutputName]] = frozenset(
    (
        # Base outputs
        ENERGY_STORAGE_POWER_CHARGE := "energy_storage_power_charge",
        ENERGY_STORAGE_POWER_DISCHARGE := "energy_storage_power_discharge",
        ENERGY_STORAGE_ENERGY_STORED := "energy_storage_energy_stored",
        # Constraint shadow prices
        ENERGY_STORAGE_POWER_BALANCE := "energy_storage_power_balance",
        ENERGY_STORAGE_ENERGY_IN_FLOW := "energy_storage_energy_in_flow",
        ENERGY_STORAGE_ENERGY_OUT_FLOW := "energy_storage_energy_out_flow",
        ENERGY_STORAGE_SOC_MAX := "energy_storage_soc_max",
        ENERGY_STORAGE_SOC_MIN := "energy_storage_soc_min",
    )
)

# Energy storage power constraints (subset of outputs that relate to power balance)
ENERGY_STORAGE_POWER_CONSTRAINTS: Final[frozenset[EnergyStorageConstraintName]] = frozenset(
    (ENERGY_STORAGE_POWER_BALANCE,)
)


class EnergyStorage(Element[EnergyStorageOutputName]):
    """Energy storage element for electrical system modeling.

    Represents a single logical partition of battery capacity with cumulative energy tracking.
    Battery devices are composed of multiple EnergyStorage partitions connected via
    EnergyBalanceConnection elements that enforce fill ordering.

    Uses TrackedParam for parameters that can change between optimizations.
    """

    # Parameters
    capacity: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_charge: TrackedParam[float] = TrackedParam()

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
        super().__init__(name=name, periods=periods, solver=solver, output_names=ENERGY_STORAGE_OUTPUT_NAMES)
        n_periods = self.n_periods

        # Set tracked parameters (broadcasts capacity to n_periods + 1)
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)
        self.initial_charge = initial_charge

        # Create all energy variables (including initial state at t=0)
        self.energy_in = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_energy_in_", out_array=True)
        self.energy_out = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_energy_out_", out_array=True)

        # Pre-calculate power and energy expressions
        self.power_consumption = (self.energy_in[1:] - self.energy_in[:-1]) * (1.0 / self.periods)
        self.power_production = (self.energy_out[1:] - self.energy_out[:-1]) * (1.0 / self.periods)
        self.stored_energy = self.energy_in - self.energy_out

    @constraint
    def energy_storage_initial_charge(self) -> highs_linear_expression:
        """Constraint: energy_in[0] == initial_charge."""
        return self.energy_in[0] == self.initial_charge

    @constraint
    def energy_storage_initial_discharge(self) -> highs_linear_expression:
        """Constraint: energy_out[0] == 0."""
        return self.energy_out[0] == 0.0

    @constraint(output=True, unit="$/kWh")
    def energy_storage_energy_in_flow(self) -> list[highs_linear_expression]:
        """Constraint: cumulative energy in can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return list(self.energy_in[1:] >= self.energy_in[:-1])

    @constraint(output=True, unit="$/kWh")
    def energy_storage_energy_out_flow(self) -> list[highs_linear_expression]:
        """Constraint: cumulative energy out can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return list(self.energy_out[1:] >= self.energy_out[:-1])

    @constraint(output=True, unit="$/kWh")
    def energy_storage_soc_max(self) -> list[highs_linear_expression]:
        """Constraint: stored energy cannot exceed capacity.

        Output: shadow price indicating the marginal value of additional capacity.
        """
        return list(self.stored_energy[1:] <= self.capacity[1:])

    @constraint(output=True, unit="$/kWh")
    def energy_storage_soc_min(self) -> list[highs_linear_expression]:
        """Constraint: stored energy cannot be negative.

        Output: shadow price indicating the marginal cost of minimum SOC constraint.
        """
        return list(self.stored_energy[1:] >= 0)

    @constraint(output=True, unit="$/kW")
    def energy_storage_power_balance(self) -> list[highs_linear_expression]:
        """Constraint: connection_power equals net storage power.

        Output: shadow price indicating the marginal value of power balance constraint.
        """
        return list(self.connection_power() == self.power_consumption - self.power_production)

    # Output methods

    @output
    def energy_storage_power_charge(self) -> OutputData:
        """Output: power being consumed to charge the storage."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
        )

    @output
    def energy_storage_power_discharge(self) -> OutputData:
        """Output: power being produced by discharging the storage."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_production), direction="+"
        )

    @output
    def energy_storage_energy_stored(self) -> OutputData:
        """Output: energy currently stored."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self.extract_values(self.stored_energy))
