"""Generic electrical entity for energy system modeling."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast

from pulp import LpConstraint, LpVariable, lpSum

from .const import (
    OUTPUT_NAME_ENERGY_STORED,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_NAME_POWER_PRODUCED,
    OUTPUT_NAME_PRICE_CONSUMPTION,
    OUTPUT_NAME_PRICE_PRODUCTION,
    OUTPUT_NAME_SHADOW_PRICE_ENERGY_BALANCE,
    OUTPUT_NAME_SHADOW_PRICE_POWER_CONSUMPTION_MAX,
    OUTPUT_NAME_SHADOW_PRICE_POWER_PRODUCTION_MAX,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
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

    # Stored constraints populated during build/solve workflow
    energy_balance_constraints: dict[int, LpConstraint] = field(init=False, default_factory=dict)
    power_balance_constraints: dict[int, LpConstraint] = field(init=False, default_factory=dict)
    power_consumption_max_constraints: dict[int, LpConstraint] = field(init=False, default_factory=dict)
    power_production_max_constraints: dict[int, LpConstraint] = field(init=False, default_factory=dict)

    def build(self) -> None:
        """Construct and store element constraints."""

        self.energy_balance_constraints.clear()
        self.power_consumption_max_constraints.clear()
        self.power_production_max_constraints.clear()

        if self.energy is not None and self.power_consumption is not None and self.power_production is not None:
            for t in range(1, len(self.energy)):
                energy_change = (
                    self.power_consumption[t - 1] * self.efficiency - self.power_production[t - 1] / self.efficiency
                ) * self.period
                constraint = cast("LpConstraint", self.energy[t] == self.energy[t - 1] + energy_change)
                constraint.name = f"{self.name}_energy_balance_{t}"
                self.energy_balance_constraints[t] = constraint

        if self.power_consumption is not None:
            for index, power_var in enumerate(self.power_consumption):
                if not isinstance(power_var, LpVariable) or power_var.upBound is None:
                    continue

                constraint = cast("LpConstraint", power_var <= float(power_var.upBound))
                constraint.name = f"{self.name}_power_consumption_max_{index}"
                self.power_consumption_max_constraints[index] = constraint

        if self.power_production is not None:
            for index, power_var in enumerate(self.power_production):
                if not isinstance(power_var, LpVariable) or power_var.upBound is None:
                    continue

                constraint = cast("LpConstraint", power_var <= float(power_var.upBound))
                constraint.name = f"{self.name}_power_production_max_{index}"
                self.power_production_max_constraints[index] = constraint

    def get_all_constraints(self) -> Sequence[LpConstraint]:
        """Return all stored constraints for this element."""

        return (
            *self.energy_balance_constraints.values(),
            *self.power_consumption_max_constraints.values(),
            *self.power_production_max_constraints.values(),
        )

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

        return cast("float", cost)

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

        if self.energy_balance_constraints:
            outputs[OUTPUT_NAME_SHADOW_PRICE_ENERGY_BALANCE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kWh",
                values=self._shadow_prices(self.energy_balance_constraints),
            )

        if self.power_consumption_max_constraints:
            outputs[OUTPUT_NAME_SHADOW_PRICE_POWER_CONSUMPTION_MAX] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._shadow_prices(self.power_consumption_max_constraints),
            )

        if self.power_production_max_constraints:
            outputs[OUTPUT_NAME_SHADOW_PRICE_POWER_PRODUCTION_MAX] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit="$/kW",
                values=self._shadow_prices(self.power_production_max_constraints),
            )

        return outputs

    @staticmethod
    def _shadow_prices(constraints: Mapping[int, LpConstraint]) -> tuple[float, ...]:
        """Return dual values for the provided constraints."""

        return tuple(
            float(pi) if (pi := getattr(constraint, "pi", None)) is not None else 0.0
            for constraint in constraints.values()
        )
