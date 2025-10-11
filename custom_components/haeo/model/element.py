"""Generic electrical entity for energy system modeling."""

from collections.abc import MutableSequence, Sequence
from dataclasses import dataclass
from typing import cast

from pulp import LpConstraint, LpVariable, lpSum


@dataclass
class Element:
    """Generic electrical entity which models the relationship between power and energy.

    All values use kW-based units:
    - Power: kW
    - Energy: kWh
    - Time (period): hours
    - Price: $/kWh
    """

    # Name of the entity
    name: str

    # Period for time step calculations (in hours)
    period: float
    n_periods: int

    # Separate power variables for consumption and production (in kW)
    power_consumption: Sequence[LpVariable | float] | None = None  # Positive when consuming
    power_production: Sequence[LpVariable | float] | None = None  # Positive when producing

    # Separate prices for consumption and production (in $/kWh)
    price_consumption: Sequence[float] | None = None  # Cost when consuming
    price_production: Sequence[float] | None = None  # Revenue when producing

    energy: Sequence[LpVariable | float] | None = None  # Energy in kWh
    efficiency: float = 1.0
    forecast: Sequence[float] | None = None  # Forecast in kW

    def constraints(self) -> Sequence[LpConstraint]:
        """Return constraints for the entity."""
        constraints: MutableSequence[LpConstraint] = []

        # Energy balance constraint using separate power variables
        if self.energy is not None and self.power_consumption is not None and self.power_production is not None:
            # Energy balance: E[t] = E[t-1] + (charge - discharge) * period
            # where charge and discharge include efficiency adjustments
            for t in range(1, len(self.energy)):
                energy_change = (
                    self.power_consumption[t - 1] * self.efficiency - self.power_production[t - 1] / self.efficiency
                ) * self.period
                constraints.append(cast("LpConstraint", self.energy[t] == self.energy[t - 1] + energy_change))

        return constraints

    def cost(self) -> float:
        """Return the cost of the entity using separate consumption/production variables.

        Units: $ = ($/kWh) * kW * period_hours
        """
        cost = 0
        # Handle separate consumption and production pricing
        if self.price_consumption is not None and self.power_consumption is not None:
            # Revenue for consumption (exporting to grid) - negative cost = revenue
            cost += lpSum(
                -price * power * self.period
                for price, power in zip(self.price_consumption, self.power_consumption, strict=False)
            )

        if self.price_production is not None and self.power_production is not None:
            # Cost for production (importing from grid)
            cost += lpSum(
                price * power * self.period
                for price, power in zip(self.price_production, self.power_production, strict=False)
            )

        return cost
