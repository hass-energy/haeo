"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_cons
import numpy as np
from numpy.typing import NDArray

from .const import OutputType
from .element import Element
from .output_data import OutputData
from .reactive import TrackedParam, constraint
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
        super().__init__(name=name, periods=periods, solver=solver)
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
    def initial_charge_constraint(self) -> highs_cons:
        """Constraint: energy_in[0] == initial_charge."""
        return self._solver.addConstr(self.energy_in[0] == self.initial_charge)

    @constraint
    def initial_discharge_constraint(self) -> highs_cons:
        """Constraint: energy_out[0] == 0."""
        return self._solver.addConstr(self.energy_out[0] == 0.0)

    @constraint
    def energy_in_flow_constraint(self) -> list[highs_cons]:
        """Constraint: cumulative energy in can only increase."""
        return self._solver.addConstrs(self.energy_in[1:] >= self.energy_in[:-1])

    @constraint
    def energy_out_flow_constraint(self) -> list[highs_cons]:
        """Constraint: cumulative energy out can only increase."""
        return self._solver.addConstrs(self.energy_out[1:] >= self.energy_out[:-1])

    @constraint
    def soc_max_constraint(self) -> list[highs_cons]:
        """Constraint: stored energy cannot exceed capacity."""
        return self._solver.addConstrs(self.stored_energy[1:] <= self.capacity[1:])

    @constraint
    def soc_min_constraint(self) -> list[highs_cons]:
        """Constraint: stored energy cannot be negative."""
        return self._solver.addConstrs(self.stored_energy[1:] >= 0)

    @constraint
    def power_balance_constraint(self) -> list[highs_cons]:
        """Constraint: connection_power equals net battery power."""
        return self._solver.addConstrs(self.connection_power() == self.power_consumption - self.power_production)

    def outputs(self) -> Mapping[BatteryOutputName, OutputData]:
        """Return battery output specifications."""
        outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_POWER_CHARGE: OutputData(
                type=OutputType.POWER,
                unit="kW",
                values=self.extract_values(self.power_consumption),
                direction="-",
            ),
            BATTERY_POWER_DISCHARGE: OutputData(
                type=OutputType.POWER,
                unit="kW",
                values=self.extract_values(self.power_production),
                direction="+",
            ),
            BATTERY_ENERGY_STORED: OutputData(
                type=OutputType.ENERGY,
                unit="kWh",
                values=self.extract_values(self.stored_energy),
            ),
        }

        # Add constraint shadow prices from applied constraints
        constraint_mapping: dict[str, tuple[BatteryConstraintName, str]] = {
            "power_balance_constraint": (BATTERY_POWER_BALANCE, "$/kW"),
            "energy_in_flow_constraint": (BATTERY_ENERGY_IN_FLOW, "$/kWh"),
            "energy_out_flow_constraint": (BATTERY_ENERGY_OUT_FLOW, "$/kWh"),
            "soc_max_constraint": (BATTERY_SOC_MAX, "$/kWh"),
            "soc_min_constraint": (BATTERY_SOC_MIN, "$/kWh"),
        }

        for method_name, (output_name, unit) in constraint_mapping.items():
            if method_name in self._applied_constraints:
                outputs[output_name] = OutputData(
                    type=OutputType.SHADOW_PRICE,
                    unit=unit,
                    values=self.extract_values(self._applied_constraints[method_name]),
                )

        return outputs
