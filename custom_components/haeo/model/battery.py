"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence

import numpy as np
from pulp import LpVariable, lpSum

from .const import (
    CONSTRAINT_NAME_ENERGY_BALANCE,
    CONSTRAINT_NAME_MAX_CHARGE_POWER,
    CONSTRAINT_NAME_MAX_DISCHARGE_POWER,
    CONSTRAINT_NAME_POWER_BALANCE,
    OUTPUT_NAME_BATTERY_STATE_OF_CHARGE,
    OUTPUT_NAME_ENERGY_STORED,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_NAME_POWER_PRODUCED,
    OUTPUT_NAME_PRICE_CONSUMPTION,
    OUTPUT_NAME_PRICE_PRODUCTION,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SOC,
    OutputData,
    OutputName,
)
from .element import Element
from .util import broadcast_to_sequence, extract_values


class Battery(Element):
    """Battery entity for electrical system modeling."""

    def __init__(
        self,
        name: str,
        period: float,
        n_periods: int,
        *,
        capacity: Sequence[float] | float,
        initial_charge_percentage: Sequence[float] | float,
        min_charge_percentage: float = 10,
        max_charge_percentage: float = 90,
        max_charge_power: Sequence[float] | float | None = None,
        max_discharge_power: Sequence[float] | float | None = None,
        efficiency: float = 99.0,
        early_charge_incentive: float = 1e-3,
        discharge_cost: float | None = None,
    ) -> None:
        """Initialize a battery entity.

        Args:
            name: Name of the battery
            period: Time period in hours
            n_periods: Number of time periods
            capacity: Battery capacity in kWh per period
            initial_charge_percentage: Initial charge percentage 0-100
            min_charge_percentage: Minimum allowed charge percentage 0-100
            max_charge_percentage: Maximum allowed charge percentage 0-100
            max_charge_power: Maximum charging power in kW per period
            max_discharge_power: Maximum discharging power in kW per period
            efficiency: Battery round-trip efficiency percentage 0-100
            early_charge_incentive: Positive value ($/kWh) that creates a small incentive
                to prefer later charging. Linearly increases from 0 to -incentive across periods.
                Default 0.001 (0.1 cents/kWh) encourages charging later when costs are equal.
            discharge_cost: Cost in $/kWh when discharging

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Broadcast capacity to n_periods
        self.capacity: list[float] = broadcast_to_sequence(capacity, n_periods)

        # Broadcast initial_charge_percentage and get first value
        initial_soc_values: list[float] = broadcast_to_sequence(initial_charge_percentage, n_periods)  # type: ignore[assignment]
        initial_soc_value: float = initial_soc_values[0]

        # Store battery-specific attributes
        self.efficiency = efficiency / 100.0  # Convert percentage to fraction

        # Broadcast charge/discharge power bounds
        charge_bounds: list[float] | None = broadcast_to_sequence(max_charge_power, n_periods)
        discharge_bounds: list[float] | None = broadcast_to_sequence(max_discharge_power, n_periods)

        # Power variables (bounds will be added as constraints)
        self.power_consumption = [
            LpVariable(name=f"{name}_power_consumption_{i}", lowBound=0) for i in range(n_periods)
        ]
        self.power_production = [LpVariable(name=f"{name}_power_production_{i}", lowBound=0) for i in range(n_periods)]

        # Energy variables
        self.energy = [
            initial_soc_value * self.capacity[0] / 100.0,
            *[
                LpVariable(
                    name=f"{name}_energy_{i}",
                    lowBound=self.capacity[i] * (min_charge_percentage / 100.0),
                    upBound=self.capacity[i] * (max_charge_percentage / 100.0),
                )
                for i in range(1, n_periods)
            ],
        ]

        # Prices
        self.price_production: list[float] | None = broadcast_to_sequence(discharge_cost, n_periods)
        self.price_consumption: list[float] = np.linspace(0, -early_charge_incentive, n_periods).tolist()

        # Build energy balance constraints: E[t] = E[t-1] + (charge - discharge) * period
        self._constraints[CONSTRAINT_NAME_ENERGY_BALANCE] = [
            self.energy[t]
            == self.energy[t - 1]
            + (self.power_consumption[t - 1] * self.efficiency - self.power_production[t - 1] / self.efficiency)
            * self.period
            for t in range(1, n_periods)
        ]

        # Add power bound constraints if specified
        if charge_bounds is not None:
            self._constraints[CONSTRAINT_NAME_MAX_CHARGE_POWER] = [
                self.power_consumption[t] <= charge_bounds[t] for t in range(n_periods)
            ]
        if discharge_bounds is not None:
            self._constraints[CONSTRAINT_NAME_MAX_DISCHARGE_POWER] = [
                self.power_production[t] <= discharge_bounds[t] for t in range(n_periods)
            ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        Energy balance constraints are already built in __init__.
        """
        self._constraints[CONSTRAINT_NAME_POWER_BALANCE] = [
            self.connection_power(t) - self.power_consumption[t] + self.power_production[t] == 0
            for t in range(self.n_periods)
        ]

    def cost(self) -> float:
        """Return the cost of the battery.

        Units: $ = ($/kWh) * kW * period_hours
        """
        cost = 0
        # Consumption pricing (incentive to charge earlier)
        cost += lpSum(
            -price * power * self.period
            for price, power in zip(self.price_consumption, self.power_consumption, strict=True)
        )

        # Production pricing (discharge cost)
        if self.price_production is not None:
            cost += lpSum(
                price * power * self.period
                for price, power in zip(self.price_production, self.power_production, strict=True)
            )

        return cost

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return battery output specifications."""
        # Add the SOC sensor output
        energy_values = np.array(extract_values(self.energy))
        capacity_array = np.array(self.capacity)
        soc_values = (energy_values / capacity_array * 100.0).tolist()

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_consumption)
            ),
            OUTPUT_NAME_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_production)
            ),
            OUTPUT_NAME_ENERGY_STORED: OutputData(
                type=OUTPUT_TYPE_ENERGY, unit="kWh", values=extract_values(self.energy)
            ),
            OUTPUT_NAME_PRICE_CONSUMPTION: OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.price_consumption)
            ),
            OUTPUT_NAME_BATTERY_STATE_OF_CHARGE: OutputData(
                type=OUTPUT_TYPE_SOC,
                unit="%",
                values=tuple(soc_values),
            ),
        }

        if self.price_production is not None:
            outputs[OUTPUT_NAME_PRICE_PRODUCTION] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.price_production)
            )

        return outputs
