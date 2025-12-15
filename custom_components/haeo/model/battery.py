"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression

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

    def update(self, **kwargs: object) -> None:
        """Update battery parameters in-place for warm start optimization.

        Supports updating:
        - capacity: Updates SOC max constraint bounds
        - initial_charge: Updates initial charge constraint bounds

        Args:
            **kwargs: Parameter values to update

        """
        h = self._solver

        # Update capacity if provided
        if "capacity" in kwargs:
            raw_capacity = kwargs["capacity"]
            # Cast to expected type for broadcast_to_sequence
            if isinstance(raw_capacity, (int, float)):
                new_capacity = broadcast_to_sequence(float(raw_capacity), self.n_periods + 1)
            elif isinstance(raw_capacity, Sequence):
                new_capacity = broadcast_to_sequence(list(raw_capacity), self.n_periods + 1)
            else:
                new_capacity = None

            if new_capacity is not None:
                self.capacity = new_capacity
                # Update SOC max constraint bounds: stored_energy[1:] <= capacity[1:]
                # The constraint is: stored_energy - capacity <= 0, so upper bound is capacity value
                soc_max_constraints = self._constraints.get(BATTERY_SOC_MAX)
                if soc_max_constraints is not None and isinstance(soc_max_constraints, list):
                    for i, cons in enumerate(soc_max_constraints):
                        # Constraint form: stored_energy[i+1] <= capacity[i+1]
                        # changeRowBounds(row_index, lower, upper) where upper = capacity[i+1]
                        h.changeRowBounds(cons.index, -float("inf"), float(self.capacity[i + 1]))

        # Update initial_charge if provided
        if "initial_charge" in kwargs:
            new_initial_charge = kwargs["initial_charge"]
            if isinstance(new_initial_charge, (int, float)):
                self.initial_charge = float(new_initial_charge)
                # Update initial charge constraint: energy_in[0] == initial_charge
                # Equality constraint has lower == upper == initial_charge
                initial_charge_constraint = self._constraints.get(BATTERY_INITIAL_CHARGE)
                if initial_charge_constraint is not None and isinstance(initial_charge_constraint, highs_cons):
                    h.changeRowBounds(initial_charge_constraint.index, self.initial_charge, self.initial_charge)

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
