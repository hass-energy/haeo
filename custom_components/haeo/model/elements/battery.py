"""Battery entity for electrical system modeling."""

from collections.abc import Sequence
from typing import Any, Final, Literal, TypedDict

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import TrackedParam, constraint, output
from custom_components.haeo.model.util import broadcast_to_sequence

# Model element type for batteries
ELEMENT_TYPE: Final = "battery"
type BatteryElementTypeName = Literal["battery"]

type FloatArray = NDArray[np.floating[Any]]

# Type for battery constraint names (shadow prices exposed as outputs)
type BatteryConstraintName = Literal[
    "battery_power_balance",
    "battery_energy_in_flow",
    "battery_energy_out_flow",
    "battery_soc_max",
    "battery_soc_min",
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

# All battery output names (includes constraint shadow prices)
BATTERY_OUTPUT_NAMES: Final[frozenset[BatteryOutputName]] = frozenset(
    (
        # Base outputs
        BATTERY_POWER_CHARGE := "battery_power_charge",
        BATTERY_POWER_DISCHARGE := "battery_power_discharge",
        BATTERY_ENERGY_STORED := "battery_energy_stored",
        # Constraint shadow prices
        BATTERY_POWER_BALANCE := "battery_power_balance",
        BATTERY_ENERGY_IN_FLOW := "battery_energy_in_flow",
        BATTERY_ENERGY_OUT_FLOW := "battery_energy_out_flow",
        BATTERY_SOC_MAX := "battery_soc_max",
        BATTERY_SOC_MIN := "battery_soc_min",
    )
)

# Battery power constraints (subset of outputs that relate to power balance)
BATTERY_POWER_CONSTRAINTS: Final[frozenset[BatteryConstraintName]] = frozenset((BATTERY_POWER_BALANCE,))


class BatteryElementConfig(TypedDict):
    """Configuration for Battery model elements."""

    element_type: BatteryElementTypeName
    name: str
    capacity: Sequence[float] | FloatArray | float
    initial_charge: float


class Battery(Element[BatteryOutputName]):
    """Battery entity for electrical system modeling.

    Represents a single battery section with cumulative energy tracking.
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
        """Initialize a battery entity.

        Args:
            name: Name of the battery
            periods: Sequence of time period durations in hours
            solver: The HiGHS solver instance for creating variables and constraints
            capacity: Battery capacity in kWh per period (T+1 values for energy boundaries)
            initial_charge: Initial charge in kWh

        """
        super().__init__(name=name, periods=periods, solver=solver, output_names=BATTERY_OUTPUT_NAMES)
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
    def battery_initial_charge(self) -> highs_linear_expression:
        """Constraint: energy_in[0] == initial_charge."""
        return self.energy_in[0] == self.initial_charge

    @constraint
    def battery_initial_discharge(self) -> highs_linear_expression:
        """Constraint: energy_out[0] == 0."""
        return self.energy_out[0] == 0.0

    @constraint(output=True, unit="$/kWh")
    def battery_energy_in_flow(self) -> list[highs_linear_expression]:
        """Constraint: cumulative energy in can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return list(self.energy_in[1:] >= self.energy_in[:-1])

    @constraint(output=True, unit="$/kWh")
    def battery_energy_out_flow(self) -> list[highs_linear_expression]:
        """Constraint: cumulative energy out can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return list(self.energy_out[1:] >= self.energy_out[:-1])

    @constraint(output=True, unit="$/kWh")
    def battery_soc_max(self) -> list[highs_linear_expression]:
        """Constraint: stored energy cannot exceed capacity.

        Output: shadow price indicating the marginal value of additional capacity.
        """
        return list(self.stored_energy[1:] <= self.capacity[1:])

    @constraint(output=True, unit="$/kWh")
    def battery_soc_min(self) -> list[highs_linear_expression]:
        """Constraint: stored energy cannot be negative.

        Output: shadow price indicating the marginal cost of minimum SOC constraint.
        """
        return list(self.stored_energy[1:] >= 0)

    @constraint(output=True, unit="$/kW")
    def battery_power_balance(self) -> list[highs_linear_expression]:
        """Constraint: connection_power equals net battery power.

        Output: shadow price indicating the marginal value of power balance constraint.
        """
        return list(self.connection_power() == self.power_consumption - self.power_production)

    # Output methods

    @output
    def battery_power_charge(self) -> OutputData:
        """Output: power being consumed to charge the battery."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
        )

    @output
    def battery_power_discharge(self) -> OutputData:
        """Output: power being produced by discharging the battery."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_production), direction="+"
        )

    @output
    def battery_energy_stored(self) -> OutputData:
        """Output: energy currently stored in the battery."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self.extract_values(self.stored_energy))
