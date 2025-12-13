"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from pulp import LpAffineExpression, LpVariable

from .const import OUTPUT_TYPE_ENERGY, OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence, extract_values

# Type for battery constraint names
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

# Battery constraint names (defined with walrus operator in frozenset)
BATTERY_CONSTRAINT_NAMES: Final[frozenset[BatteryConstraintName]] = frozenset(
    (
        BATTERY_POWER_BALANCE := "battery_power_balance",
        BATTERY_ENERGY_IN_FLOW := "battery_energy_in_flow",
        BATTERY_ENERGY_OUT_FLOW := "battery_energy_out_flow",
        BATTERY_SOC_MAX := "battery_soc_max",
        BATTERY_SOC_MIN := "battery_soc_min",
    )
)

# Battery power constraints (subset of all constraints)
BATTERY_POWER_CONSTRAINTS: Final[frozenset[BatteryConstraintName]] = frozenset((BATTERY_POWER_BALANCE,))

# Battery output names (defined with walrus operator in frozenset)
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
    Multi-section batteries are composed at the element adapter layer using
    multiple Battery instances connected through a common node.
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        capacity: Sequence[float] | float,
        initial_charge: float,
    ) -> None:
        """Initialize a battery entity.

        Args:
            name: Name of the battery
            periods: Sequence of time period durations in hours
            capacity: Battery capacity in kWh per period (T+1 values for energy boundaries)
            initial_charge: Initial charge in kWh

        """
        super().__init__(name=name, periods=periods)
        n_periods = self.n_periods

        # Broadcast capacity to n_periods + 1 (energy boundaries)
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)

        # Initial charge is set as constant, not variable
        self.energy_in: list[LpAffineExpression | LpVariable] = [
            LpAffineExpression(constant=float(initial_charge)),
            *[LpVariable(f"{name}_energy_in_t{t}", lowBound=0.0) for t in range(1, n_periods + 1)],
        ]
        # Initial discharge is always 0
        self.energy_out: list[LpAffineExpression | LpVariable] = [
            LpAffineExpression(constant=0.0),
            *[LpVariable(f"{name}_energy_out_t{t}", lowBound=0.0) for t in range(1, n_periods + 1)],
        ]

        # Energy flow constraints (cumulative energy can only increase)
        self._constraints[BATTERY_ENERGY_IN_FLOW] = [
            self.energy_in[t + 1] >= self.energy_in[t] for t in range(n_periods)
        ]
        self._constraints[BATTERY_ENERGY_OUT_FLOW] = [
            self.energy_out[t + 1] >= self.energy_out[t] for t in range(n_periods)
        ]

        # SOC constraints (net energy must stay within capacity)
        self._constraints[BATTERY_SOC_MAX] = [
            self.energy_in[t + 1] - self.energy_out[t + 1] <= self.capacity[t + 1] for t in range(n_periods)
        ]
        self._constraints[BATTERY_SOC_MIN] = [
            self.energy_in[t + 1] - self.energy_out[t + 1] >= 0 for t in range(n_periods)
        ]

        # Pre-calculate power and energy expressions to avoid recomputing them
        self.power_consumption: Sequence[LpAffineExpression] = [
            (self.energy_in[t + 1] - self.energy_in[t]) / self.periods[t] for t in range(n_periods)
        ]
        self.power_production: Sequence[LpAffineExpression] = [
            (self.energy_out[t + 1] - self.energy_out[t]) / self.periods[t] for t in range(n_periods)
        ]
        self.stored_energy: Sequence[LpAffineExpression] = [
            self.energy_in[t] - self.energy_out[t] for t in range(n_periods + 1)
        ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        """

        # Power balance: connection_power equals net battery power
        self._constraints[BATTERY_POWER_BALANCE] = [
            self.connection_power(t) == self.power_consumption[t] - self.power_production[t]
            for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the battery.

        Battery costs (charge/discharge pricing, early charge incentives) are now
        handled by connections in the element adapter layer.
        """
        return []

    def outputs(self) -> Mapping[BatteryOutputName, OutputData]:
        """Return battery output specifications."""
        # Get stored energy values
        energy_values = extract_values(self.stored_energy)

        outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_POWER_CHARGE: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_consumption, direction="-"
            ),
            BATTERY_POWER_DISCHARGE: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_production, direction="+"
            ),
            BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=energy_values),
        }

        # Add constraint shadow prices
        for constraint_name in self._constraints:
            unit = "$/kW" if constraint_name in BATTERY_POWER_CONSTRAINTS else "$/kWh"
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit=unit,
                values=self._constraints[constraint_name],
            )

        return outputs
