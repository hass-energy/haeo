"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from pulp import LpAffineExpression, LpConstraint, LpVariable
from pulp.pulp import lpSum

from .const import (
    CONSTRAINT_NAME_MAX_CHARGE_POWER,
    CONSTRAINT_NAME_MAX_DISCHARGE_POWER,
    CONSTRAINT_NAME_POWER_BALANCE,
    OUTPUT_NAME_BATTERY_STATE_OF_CHARGE,
    OUTPUT_NAME_ENERGY_STORED,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_NAME_POWER_PRODUCED,
    OUTPUT_NAME_PRICE_CONSUMPTION,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_SOC,
    OutputData,
    OutputName,
)
from .element import Element
from .util import broadcast_to_sequence, extract_values


class BatterySection:
    """Represents a battery SOC section with cumulative energy variables."""

    def __init__(
        self,
        *,
        name: str,
        capacity: Sequence[float],
        charge_cost: Sequence[float],
        discharge_cost: Sequence[float],
        initial_charge: float,
        period: float,
        n_periods: int,
    ) -> None:
        self.name = name
        self.capacity = capacity
        self.charge_cost = [LpAffineExpression(constant=float(c)) for c in charge_cost]
        self.discharge_cost = [LpAffineExpression(constant=float(c)) for c in discharge_cost]
        self.period = period
        self.n_periods = n_periods

        # Initial charge is set based rather than variable
        self.energy_in: list[LpAffineExpression | LpVariable] = [
            LpAffineExpression(constant=float(initial_charge)),
            *[LpVariable(f"{name}_energy_in_t{t}", lowBound=0.0) for t in range(1, n_periods + 1)],
        ]
        self.energy_out: list[LpAffineExpression | LpVariable] = [
            LpVariable(f"{name}_energy_out_t{t}", lowBound=0.0) for t in range(n_periods + 1)
        ]

        self.constraints = {
            "monotonic_charge": [self.energy_in[t + 1] >= self.energy_in[t] for t in range(n_periods)],
            "monotonic_discharge": [self.energy_out[t + 1] >= self.energy_out[t] for t in range(n_periods)],
            "capacity_upper": [
                self.energy_in[t + 1] - self.energy_out[t + 1] <= capacity[t + 1] for t in range(n_periods)
            ],
            "capacity_lower": [self.energy_in[t + 1] - self.energy_out[t + 1] >= 0 for t in range(n_periods)],
        }

    @property
    def power_consumption(self) -> Sequence[LpAffineExpression]:
        """Return the power consumption of the section."""
        return [(self.energy_in[t + 1] - self.energy_in[t]) / self.period for t in range(self.n_periods)]

    @property
    def power_production(self) -> Sequence[LpAffineExpression]:
        """Return the power production of the section."""
        return [(self.energy_out[t + 1] - self.energy_out[t]) / self.period for t in range(self.n_periods)]

    @property
    def stored_energy(self) -> Sequence[LpAffineExpression]:
        """Return the stored energy of the section."""
        return [self.energy_in[t] - self.energy_out[t] for t in range(self.n_periods + 1)]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost of the section."""
        return [
            *[(self.energy_in[t + 1] - self.energy_in[t]) * self.charge_cost[t] for t in range(self.n_periods)],
            *[(self.energy_out[t + 1] - self.energy_out[t]) * self.discharge_cost[t] for t in range(self.n_periods)],
        ]


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
        discharge_cost: Sequence[float] | float | None = None,
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

        # Extract all the simple parameters we will need later
        self.efficiency = broadcast_to_sequence(efficiency, n_periods)
        
        # Convert all parameters to sequences
        capacity_seq = broadcast_to_sequence(capacity, n_periods)
        min_charge_percentage = broadcast_to_sequence(min_charge_percentage, n_periods)
        max_charge_percentage = broadcast_to_sequence(max_charge_percentage, n_periods)
        undercharge_percentage = broadcast_to_sequence(undercharge_percentage, n_periods)
        overcharge_percentage = broadcast_to_sequence(overcharge_percentage, n_periods)
        undercharge_cost_seq = broadcast_to_sequence(undercharge_cost, n_periods)
        overcharge_cost_seq = broadcast_to_sequence(overcharge_cost, n_periods)
        discharge_cost_seq = broadcast_to_sequence(discharge_cost, n_periods)
        max_charge_power_seq = broadcast_to_sequence(max_charge_power, n_periods)
        max_discharge_power_seq = broadcast_to_sequence(max_discharge_power, n_periods)
        
        # Extend capacity to n_periods+1 by repeating last value (for energy state variables)
        capacity_extended = [*capacity_seq, capacity_seq[-1]]
        
        # Validate percentage ordering for all time periods
        if min_charge_percentage and max_charge_percentage:
            for t in range(len(min_charge_percentage)):
                if min_charge_percentage[t] >= max_charge_percentage[t]:
                    msg = (
                        f"min_charge_percentage ({min_charge_percentage[t]}) "
                        f"must be less than max_charge_percentage ({max_charge_percentage[t]}) "
                        f"at time period {t}"
                    )
                    raise ValueError(msg)

        if undercharge_percentage and min_charge_percentage:
            for t in range(len(undercharge_percentage)):
                if undercharge_percentage[t] >= min_charge_percentage[t]:
                    msg = (
                        f"undercharge_percentage ({undercharge_percentage[t]}) "
                        f"must be less than min_charge_percentage ({min_charge_percentage[t]}) "
                        f"at time period {t}"
                    )
                    raise ValueError(msg)

        if max_charge_percentage and overcharge_percentage:
            for t in range(len(max_charge_percentage)):
                if max_charge_percentage[t] >= overcharge_percentage[t]:
                    msg = (
                        f"overcharge_percentage ({overcharge_percentage[t]}) "
                        f"must be greater than max_charge_percentage ({max_charge_percentage[t]}) "
                        f"at time period {t}"
                    )
                    raise ValueError(msg)

        # Get the first value of initial_charge_percentage and convert to energy
        initial_soc = broadcast_to_sequence(initial_charge_percentage, n_periods)[0]

        # From the early charge value, make two incentives, one for charging early and one for discharging early.
        # We will also multiply these values for each section to make it more/less attractive.
        # This also makes a small spread between charging and discharging which helps prevent oscillation.
        charge_early_incentive = np.linspace(-early_charge_incentive, 0.0, n_periods)
        discharge_early_incentive = np.linspace(0.0, early_charge_incentive, n_periods)

        # This is the energy that is unusable due to being below absolute minimum percentage
        unusable_percentage = undercharge_percentage if undercharge_percentage is not None else min_charge_percentage
        self.inaccessible_energy: Sequence[float] = (np.array(unusable_percentage) / 100.0 * np.array(capacity_extended)).tolist()

        # Calculate initial charge in kWh (remove unusable percentage)
        initial_charge = (initial_soc - unusable_percentage[0]) / 100.0 * capacity_seq[0]

        self._sections: list[BatterySection] = []
        if undercharge_percentage is not None and undercharge_cost_seq is not None:
            undercharge_range = (np.array(min_charge_percentage) - np.array(undercharge_percentage)) / 100.0
            undercharge_capacity = (undercharge_range * np.array(capacity_extended)).tolist()
            section_initial = min(max(initial_charge, 0.0), undercharge_capacity[0])
            self._sections.append(
                BatterySection(
                    name="undercharge",
                    capacity=undercharge_capacity,
                    charge_cost=(charge_early_incentive * 3).tolist(),
                    discharge_cost=((discharge_early_incentive * 1) + np.array(undercharge_cost_seq)).tolist(),
                    initial_charge=section_initial,
                    period=period,
                    n_periods=n_periods,
                )
            )
            initial_charge -= section_initial

        normal_range = (np.array(max_charge_percentage) - np.array(min_charge_percentage)) / 100.0
        normal_capacity = (normal_range * np.array(capacity_extended)).tolist()
        section_initial = min(max(initial_charge, 0.0), normal_capacity[0])
        self._sections.append(
            BatterySection(
                name="normal",
                capacity=normal_capacity,
                charge_cost=(charge_early_incentive * 2).tolist(),
                discharge_cost=((discharge_early_incentive * 2) + np.array(discharge_cost_seq)).tolist(),
                initial_charge=section_initial,
                period=period,
                n_periods=n_periods,
            )
        )
        initial_charge -= section_initial

        if overcharge_percentage is not None and overcharge_cost_seq is not None:
            overcharge_range = (np.array(overcharge_percentage) - np.array(max_charge_percentage)) / 100.0
            overcharge_capacity = (overcharge_range * np.array(capacity_extended)).tolist()
            section_initial = min(max(initial_charge, 0.0), overcharge_capacity[0])
            self._sections.append(
                BatterySection(
                    name="overcharge",
                    capacity=overcharge_capacity,
                    charge_cost=((charge_early_incentive * 1) + np.array(overcharge_cost_seq)).tolist(),
                    discharge_cost=((discharge_early_incentive * 3) + np.array(discharge_cost_seq)).tolist(),
                    initial_charge=section_initial,
                    period=period,
                    n_periods=n_periods,
                )
            )
        
        # Add section constraints to battery constraints
        for section in self._sections:
            for constraint_name, constraint_list in section.constraints.items():
                self._constraints[f"{section.name}_{constraint_name}"] = constraint_list

        if max_charge_power is not None or max_discharge_power is not None:
            # Make the power limits constraints by measuring relative power consumption
            total_power = [
                lpSum(s.power_consumption[t] - s.power_production[t] for s in self._sections)
                for t in range(self.n_periods)
            ]

            # Total power must be within charge/discharge limits
            if self.max_charge_power is not None:
                self._constraints[CONSTRAINT_NAME_MAX_CHARGE_POWER] = [
                    total_power[t] <= self.max_charge_power[t] for t in range(self.n_periods)
                ]
            if self.max_discharge_power is not None:
                self._constraints[CONSTRAINT_NAME_MAX_DISCHARGE_POWER] = [
                    -total_power[t] <= self.max_discharge_power[t] for t in range(self.n_periods)
                ]

    @property
    def power_consumption(self) -> Sequence[LpAffineExpression]:
        """Return the power consumption of the battery."""
        return [s.power_consumption[t] for t in range(self.n_periods) for s in self._sections]

    @property
    def power_production(self) -> Sequence[LpAffineExpression]:
        """Return the power production of the battery."""
        return [s.power_production[t] for t in range(self.n_periods) for s in self._sections]

    @property
    def stored_energy(self) -> Sequence[LpAffineExpression]:
        """Return the stored energy of the battery."""
        return [
            self.inaccessible_energy[t] + lpSum(s.energy_in[t] - s.energy_out[t] for s in self._sections)
            for t in range(self.n_periods)
        ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        Efficiency losses are applied to prevent oscillation (cycling).
        """
        # Power balance with efficiency:
        # - When charging (connection_power > 0): stored energy = connection_power * efficiency * period
        # - When discharging (connection_power < 0): connection_power = stored energy * efficiency
        #
        # Since we can't easily split charging/discharging in LP, we apply efficiency to connection_power:
        # connection_power * efficiency * period = net internal energy change
        #
        # This means:
        # - Charging: Less energy stored than power consumed (efficiency loss)
        # - Discharging: Less power delivered than energy extracted (efficiency loss)
        self._constraints[CONSTRAINT_NAME_POWER_BALANCE] = [
            self.connection_power(t) * (self.efficiency[t] / 100.0) * self.period
            == lpSum(
                (s.energy_in[t + 1] - s.energy_in[t]) - (s.energy_out[t + 1] - s.energy_out[t]) for s in self.sections
            )
            for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the battery using multi-section approach."""
        costs: list[LpAffineExpression] = []

        # Sum costs from all sections
        for s in self._sections:
            costs.extend(s.cost())

        return costs

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return battery output specifications."""

        # Convert to SOC percentage
        capacity_array = np.array(self.capacity)[:-1]  # Use n_periods values
        soc_values = (np.array(total_energy_values) / capacity_array * 100.0).tolist()

        # Extract the early charge incentive values for price_consumption output
        price_consumption_values = tuple(extract_values(self.early_charge_incentive))

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(self.power_consumption))
            ),
            OUTPUT_NAME_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(self.power_production))
            ),
            OUTPUT_NAME_ENERGY_STORED: OutputData(
                type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(extract_values(self.stored_energy))
            ),
            OUTPUT_NAME_BATTERY_STATE_OF_CHARGE: OutputData(
                type=OUTPUT_TYPE_SOC,
                unit="%",
                values=tuple(soc_values),
            ),
        }

        for section in self._sections:
            outputs.update(
                {
                    f"{section.name}_{OUTPUT_NAME_ENERGY_STORED}": OutputData(
                        type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(extract_values(section.stored_energy))
                    ),
                    f"{section.name}_{OUTPUT_NAME_POWER_PRODUCED}": OutputData(
                        type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(section.power_production))
                    ),
                    f"{section.name}_{OUTPUT_NAME_POWER_CONSUMED}": OutputData(
                        type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(section.power_consumption))
                    ),
                    f"{section.name}_{OUTPUT_NAME_PRICE_CONSUMPTION}": OutputData(
                        type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=tuple(extract_values(section.charge_cost))
                    ),
                    f"{section.name}_{OUTPUT_NAME_PRICE_PRODUCTION}": OutputData(
                        type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=tuple(extract_values(section.discharge_cost))
                    ),
                }
            )

        return outputs
