"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from pulp import LpAffineExpression, LpConstraint, LpVariable
from pulp.pulp import lpSum, value

from .const import (
    CONSTRAINT_NAME_POWER_BALANCE,
    OUTPUT_NAME_BATTERY_STATE_OF_CHARGE,
    OUTPUT_NAME_ENERGY_STORED,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_NAME_POWER_PRODUCED,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_SOC,
    OutputData,
    OutputName,
)
from .element import Element
from .util import broadcast_to_sequence, extract_values


@dataclass
class BatterySection:
    """Represents a battery SOC section with cumulative energy variables."""

    name: str
    lower_percentage: list[LpAffineExpression]
    upper_percentage: list[LpAffineExpression]
    virtual_capacity: list[LpAffineExpression]
    energy_in: list[LpAffineExpression | LpVariable]
    energy_out: list[LpAffineExpression | LpVariable]
    charge_cost: list[LpAffineExpression] | None
    discharge_cost: list[LpAffineExpression] | None
    constraints: Mapping[str, list[LpConstraint]]


class Battery(Element):
    """Battery entity for electrical system modeling using multi-section approach."""

    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
        *,
        capacity: Sequence[float] | float,
        initial_charge_percentage: Sequence[float] | float,
        min_charge_percentage: Sequence[float] | float = 10,
        max_charge_percentage: Sequence[float] | float = 90,
        max_charge_power: Sequence[float] | float | None = None,
        max_discharge_power: Sequence[float] | float | None = None,
        efficiency: Sequence[float] | float = 99.0,
        early_charge_incentive: float = 1e-3,
        discharge_cost: float | None = None,
        undercharge_percentage: Sequence[float] | float | None = None,
        overcharge_percentage: Sequence[float] | float | None = None,
        undercharge_cost: Sequence[float] | float | None = None,
        overcharge_cost: Sequence[float] | float | None = None,
    ) -> None:
        """Initialize a battery entity with multi-section modeling.

        Args:
            name: Name of the battery
            period: Time period in hours
            n_periods: Number of time periods
            capacity: Battery capacity in kWh per period
            initial_charge_percentage: Initial charge percentage 0-100
            min_charge_percentage: Preferred minimum charge percentage (inner bound) 0-100
            max_charge_percentage: Preferred maximum charge percentage (inner bound) 0-100
            max_charge_power: Maximum charging power in kW per period
            max_discharge_power: Maximum discharging power in kW per period
            efficiency: Battery round-trip efficiency percentage 0-100
            early_charge_incentive: Positive value ($/kWh) that creates a small incentive
                to prefer earlier charging. Linearly increases from 0 to -incentive across periods.
                Default 0.001 (0.1 cents/kWh) encourages charging earlier when costs are equal.
            discharge_cost: Cost in $/kWh when discharging (applies to normal section)
            undercharge_percentage: Absolute minimum charge percentage (outer bound) 0-100
            overcharge_percentage: Absolute maximum charge percentage (outer bound) 0-100
            undercharge_cost: Cost in $/kWh for discharging in undercharge section
            overcharge_cost: Cost in $/kWh for charging in overcharge section

        Raises:
            ValueError: If percentage parameters violate ordering constraints

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Broadcast initial_charge_percentage and get first value
        initial_soc_values = broadcast_to_sequence(initial_charge_percentage, n_periods)
        self.initial_soc_value: float = value(initial_soc_values[0])

        # Early charging incentive linearly increasing from 0 to -incentive (higher costs later)
        self.early_charge_incentive = [
            LpAffineExpression(constant=v) for v in np.linspace(0, -early_charge_incentive, n_periods).tolist()
        ]

        # Convert all parameters to sequences
        self.efficiency = broadcast_to_sequence(efficiency, n_periods)
        self.min_charge_percentage = broadcast_to_sequence(min_charge_percentage, n_periods)
        self.max_charge_percentage = broadcast_to_sequence(max_charge_percentage, n_periods)
        self.undercharge_percentage = broadcast_to_sequence(undercharge_percentage, n_periods)
        self.overcharge_percentage = broadcast_to_sequence(overcharge_percentage, n_periods)
        self.capacity = broadcast_to_sequence(capacity, n_periods)
        self.overcharge_cost = broadcast_to_sequence(overcharge_cost, n_periods)
        self.undercharge_cost = broadcast_to_sequence(undercharge_cost, n_periods)
        self.discharge_cost = broadcast_to_sequence(discharge_cost, n_periods)

        self.max_charge_power = broadcast_to_sequence(max_charge_power, n_periods)
        self.max_discharge_power = broadcast_to_sequence(max_discharge_power, n_periods)

        # This is the energy below the minimum charge level which won't show up in any section
        self.inaccessible_energy = [
            v * c for v, c in zip(self.undercharge_percentage or self.min_charge_percentage, self.capacity, strict=True)
        ]

        # This is the amount of energy to distribute among sections at the start
        initial_charged = (
            (
                self.initial_soc_value - value(self.undercharge_percentage[0])
                if self.undercharge_percentage
                else value(self.min_charge_percentage[0])
            )
            / 100.0
            * value(self.capacity[0])
        )

        # Create the battery sections
        self.sections: list[BatterySection] = []
        for low, high, in_cost, out_cost in (
            (self.undercharge_percentage, self.min_charge_percentage, None, self.undercharge_cost),
            (self.min_charge_percentage, self.max_charge_percentage, self.early_charge_incentive, self.discharge_cost),
            (self.max_charge_percentage, self.overcharge_percentage, self.overcharge_cost, None),
        ):
            # Skip unreferenced sections
            if low is None or high is None:
                continue

            # The capacity of this section
            section_capacity = [(hi - lo) / 100.0 * cap for lo, hi, cap in zip(low, high, self.capacity, strict=True)]

            # Assign initial charged energy to this section
            section_charged = min(initial_charged, value(section_capacity[0]), 0.0)
            initial_charged -= section_charged

            # Create cumulative energy charged/discharged variables for this section (+1 to include the initial state)
            energy_in: list[LpAffineExpression | LpVariable] = [
                LpAffineExpression(constant=initial_charged),
                *[LpVariable(f"{self.name}_energy_in_t{t}", lowBound=0.0) for t in range(self.n_periods + 1)],
            ]
            energy_out: list[LpAffineExpression | LpVariable] = [
                LpAffineExpression(constant=0.0),
                *[LpVariable(f"{self.name}_energy_out_t{t}", lowBound=0.0) for t in range(self.n_periods + 1)],
            ]

            constraints = {
                "monotonic_charge": [energy_in[t + 1] >= energy_in[t] for t in range(self.n_periods)],
                "monotonic_discharge": [energy_out[t + 1] >= energy_out[t] for t in range(self.n_periods)],
                "capacity_limit": [energy_in[t] - energy_out[t] <= section_capacity[t] for t in range(self.n_periods)],
            }

            self.sections.append(
                BatterySection(
                    name=f"{self.name}_section_{low[0]}_{high[0]}",
                    lower_percentage=low,
                    upper_percentage=high,
                    virtual_capacity=section_capacity,
                    energy_in=energy_in,
                    energy_out=energy_out,
                    charge_cost=in_cost,
                    discharge_cost=out_cost,
                    constraints=constraints,
                )
            )

        # Make the order of charge constraints
        for a, b in zip(self.sections[:-1], self.sections[1:], strict=True):
            # Previous section must be full before charging the next section
            a_soc = [(a.energy_in[t] - a.energy_out[t]) / a.virtual_capacity[t] for t in range(self.n_periods + 1)]
            b_soc = [(b.energy_in[t] - b.energy_out[t]) / b.virtual_capacity[t] for t in range(self.n_periods + 1)]

            # Previous section must be charged before next section can be charged
            self._constraints[f"section_ordering_{a.name}_{b.name}"] = [
                a_soc[t] <= b_soc[t] for t in range(self.n_periods + 1)
            ]

        if self.max_charge_power is not None or self.max_discharge_power is not None:
            # Make the power limits constraints
            total_power = [
                lpSum(s.energy_in[t] - s.energy_out[t] for s in self.sections) for t in range(self.n_periods + 1)
            ]

            # Total power must be within charge/discharge limits
            if self.max_charge_power is not None:
                self._constraints["max_charge_power"] = [
                    total_power[t] <= self.max_charge_power[t] for t in range(self.n_periods)
                ]
            if self.max_discharge_power is not None:
                self._constraints["max_discharge_power"] = [
                    -total_power[t] <= self.max_discharge_power[t] for t in range(self.n_periods)
                ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        Energy balance constraints are already built in __init__.
        """
        # Power flow
        total_power = [
            lpSum(s.energy_in[t] - s.energy_out[t] for s in self.sections) for t in range(self.n_periods + 1)
        ]
        self._constraints[CONSTRAINT_NAME_POWER_BALANCE] = [
            total_power[t] == self.connection_power(t) for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the battery using multi-section approach."""
        costs: list[LpAffineExpression] = []

        # Sum costs from all sections
        for s in self.sections:
            # Cost for charging this section
            if s.charge_cost is not None:
                costs.extend([(s.energy_in[t + 1] - s.energy_in[t]) * s.charge_cost[t] for t in range(self.n_periods)])

            # Cost for discharging this section
            if s.discharge_cost is not None:
                costs.extend(
                    [(s.energy_out[t + 1] - s.energy_out[t]) * s.discharge_cost[t] for t in range(self.n_periods)]
                )

        return costs

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return battery output specifications."""
        # Calculate total SOC from all sections
        total_energy_values: list[float] = []

        # Get all the energy in/out values
        energy_in = np.zeros(self.n_periods)
        energy_out = np.zeros(self.n_periods)
        for s in self.sections:
            energy_in += np.array(extract_values(s.energy_in))
            energy_out += np.array(extract_values(s.energy_out))

        # Our total energy stored is the difference between energy in and out, plus any inaccessible energy (energy below minimum charge)
        total_energy_values = ((energy_in - energy_out)[:-1] + np.array(self.inaccessible_energy)).tolist()
        power_consumption = (energy_in - energy_in[:-1]) / self.period
        power_production = (energy_out - energy_out[:-1]) / self.period

        # Convert to SOC percentage
        capacity_array = np.array(self.capacity)
        soc_values = (np.array(total_energy_values) / capacity_array * 100.0).tolist()

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(power_consumption)
            ),
            OUTPUT_NAME_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(power_production)
            ),
            OUTPUT_NAME_ENERGY_STORED: OutputData(
                type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(total_energy_values)
            ),
            OUTPUT_NAME_BATTERY_STATE_OF_CHARGE: OutputData(
                type=OUTPUT_TYPE_SOC,
                unit="%",
                values=tuple(soc_values),
            ),
        }

        return outputs
