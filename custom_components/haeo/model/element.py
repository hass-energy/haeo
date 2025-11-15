"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass

from pulp import LpAffineExpression, LpConstraint, LpVariable, lpSum

from .const import (
    OUTPUT_NAME_ENERGY_STORED,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_NAME_POWER_PRODUCED,
    OUTPUT_NAME_PRICE_CONSUMPTION,
    OUTPUT_NAME_PRICE_PRODUCTION,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OutputData,
    OutputName,
    extract_values,
)


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
    price_consumption: Sequence[LpVariable | float] | None = None  # Cost when consuming
    price_production: Sequence[LpVariable | float] | None = None  # Revenue when producing

    # Energy storage
    energy: Sequence[LpVariable | float] | None = None  # Energy in kWh
    efficiency: float = 1.0

    def constraints(self) -> Sequence[LpConstraint]:
        """Return constraints for the entity."""
        constraints: MutableSequence[LpConstraint] = []

        # Energy balance constraint using separate power variables
        if self.energy is not None and self.power_consumption is not None and self.power_production is not None:
            # Energy balance: E[t] = E[t-1] + (charge - discharge) * period
            # where charge and discharge include efficiency adjustments
            # Note: energy[0] is initial value (float), energy[t] for t >= 1 are LpVariables
            for t in range(1, len(self.energy)):
                energy_t = self.energy[t]
                energy_prev = self.energy[t - 1]

                # Type narrowing: By construction, energy[t] for t >= 1 is always LpVariable
                # and energy[0] is always float. We verify this at runtime.
                if not isinstance(energy_t, LpVariable):
                    continue  # Skip if not a variable (shouldn't happen by construction)

                energy_change = (
                    self.power_consumption[t - 1] * self.efficiency - self.power_production[t - 1] / self.efficiency
                ) * self.period
                constraints.append(energy_t == energy_prev + energy_change)

        return constraints

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the entity using separate consumption/production variables.

        Returns a sequence of cost expressions for aggregation at the network level.

        Units: $ = ($/kWh) * kW * period_hours
        """
        costs: list[LpAffineExpression] = []
        # Handle separate consumption and production pricing
        if self.price_consumption is not None and self.power_consumption is not None:
            # Revenue for consumption (exporting to grid) - negative cost = revenue
            costs.append(
                lpSum(
                    -price * power * self.period
                    for price, power in zip(self.price_consumption, self.power_consumption, strict=True)
                )
            )

        if self.price_production is not None and self.power_production is not None:
            # Cost for production (importing from grid)
            costs.append(
                lpSum(
                    price * power * self.period
                    for price, power in zip(self.price_production, self.power_production, strict=True)
                )
            )

        return costs

    def get_outputs(self) -> Mapping[OutputName, OutputData]:
        """Return output specifications for the element."""

        outputs: dict[OutputName, OutputData] = {}
        if self.power_consumption is not None:
            outputs[OUTPUT_NAME_POWER_CONSUMED] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_consumption)
            )

        if self.power_production is not None:
            outputs[OUTPUT_NAME_POWER_PRODUCED] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_production)
            )

        if self.energy is not None:
            outputs[OUTPUT_NAME_ENERGY_STORED] = OutputData(
                type=OUTPUT_TYPE_ENERGY, unit="kWh", values=extract_values(self.energy)
            )

        if self.price_consumption is not None:
            outputs[OUTPUT_NAME_PRICE_CONSUMPTION] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.price_consumption)
            )
        if self.price_production is not None:
            outputs[OUTPUT_NAME_PRICE_PRODUCTION] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=extract_values(self.price_production)
            )

        return outputs
