"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, MutableSequence, Sequence

import numpy as np
from pulp import LpConstraint, LpVariable, lpSum

from .const import OUTPUT_NAME_BATTERY_STATE_OF_CHARGE, OUTPUT_TYPE_SOC, OutputData, OutputName, extract_values
from .element import Element


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
        charge_cost: float | None = None,
        discharge_cost: float | None = None,
        soft_min_charge_percentage: float | None = None,
        soft_max_charge_percentage: float | None = None,
        undercharge_cost: Sequence[float] | float | None = None,
        overcharge_cost: Sequence[float] | float | None = None,
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
            charge_cost: Cost in $/kWh when charging
            discharge_cost: Cost in $/kWh when discharging
            soft_min_charge_percentage: Soft minimum charge percentage for undercharge slack
            soft_max_charge_percentage: Soft maximum charge percentage for overcharge slack
            undercharge_cost: Cost in $/kWh for operating below soft minimum
            overcharge_cost: Cost in $/kWh for operating above soft maximum

        """
        # Broadcast capacity to n_periods using numpy
        capacity_array = np.broadcast_to(np.atleast_1d(capacity), (n_periods,))
        capacity_values = capacity_array.tolist()

        # Broadcast initial_charge_percentage and get first value
        initial_soc_array = np.broadcast_to(np.atleast_1d(initial_charge_percentage), (n_periods,))
        initial_soc_value = float(initial_soc_array[0])

        self.capacity = capacity_values
        self.min_charge_percentage = min_charge_percentage
        self.max_charge_percentage = max_charge_percentage
        self.soft_min_charge_percentage = soft_min_charge_percentage
        self.soft_max_charge_percentage = soft_max_charge_percentage

        # Broadcast charge/discharge power bounds
        if max_charge_power is not None:
            charge_array = np.broadcast_to(np.atleast_1d(max_charge_power), (n_periods,))
            charge_bounds = charge_array.tolist()
        else:
            charge_bounds = [None] * n_periods

        if max_discharge_power is not None:
            discharge_array = np.broadcast_to(np.atleast_1d(max_discharge_power), (n_periods,))
            discharge_bounds = discharge_array.tolist()
        else:
            discharge_bounds = [None] * n_periods

        # Create slack variables for soft limits if configured
        self.overcharge_slack: Sequence[LpVariable] | None = None
        self.undercharge_slack: Sequence[LpVariable] | None = None
        self.overcharge_cost_values: list[float] | None = None
        self.undercharge_cost_values: list[float] | None = None

        if soft_max_charge_percentage is not None and overcharge_cost is not None:
            overcharge_cost_array = np.broadcast_to(np.atleast_1d(overcharge_cost), (n_periods,))
            self.overcharge_cost_values = overcharge_cost_array.tolist()
            max_overcharge = capacity_array * (max_charge_percentage - soft_max_charge_percentage) / 100.0
            self.overcharge_slack = [
                LpVariable(
                    name=f"{name}_overcharge_slack_{i}",
                    lowBound=0,
                    upBound=float(max_overcharge[i]),
                )
                for i in range(n_periods - 1)
            ]

        if soft_min_charge_percentage is not None and undercharge_cost is not None:
            undercharge_cost_array = np.broadcast_to(np.atleast_1d(undercharge_cost), (n_periods,))
            self.undercharge_cost_values = undercharge_cost_array.tolist()
            max_undercharge = capacity_array * (soft_min_charge_percentage - min_charge_percentage) / 100.0
            self.undercharge_slack = [
                LpVariable(
                    name=f"{name}_undercharge_slack_{i}",
                    lowBound=0,
                    upBound=float(max_undercharge[i]),
                )
                for i in range(n_periods - 1)
            ]

        super().__init__(
            name=name,
            period=period,
            n_periods=n_periods,
            power_consumption=[
                LpVariable(name=f"{name}_power_consumption_{i}", lowBound=0, upBound=charge_bounds[i])
                for i in range(n_periods)
            ],
            power_production=[
                LpVariable(name=f"{name}_power_production_{i}", lowBound=0, upBound=discharge_bounds[i])
                for i in range(n_periods)
            ],
            energy=[
                initial_soc_value * capacity_values[0] / 100.0,
                *[
                    LpVariable(
                        name=f"{name}_energy_{i}",
                        lowBound=capacity_values[i] * (min_charge_percentage / 100.0),
                        upBound=capacity_values[i] * (max_charge_percentage / 100.0),
                    )
                    for i in range(n_periods - 1)
                ],
            ],
            efficiency=efficiency / 100.0,  # Convert percentage to fraction
            price_production=(np.ones(n_periods) * discharge_cost).tolist() if discharge_cost is not None else None,
            price_consumption=np.linspace(0, charge_cost, n_periods).tolist() if charge_cost is not None else None,
        )

    def constraints(self) -> Sequence[LpConstraint]:
        """Return constraints for the battery including soft limit constraints."""
        constraints: MutableSequence[LpConstraint] = list(super().constraints())

        if self.energy is None:
            return constraints

        # Add soft maximum constraint (overcharge)
        if self.overcharge_slack is not None and self.soft_max_charge_percentage is not None:
            for t in range(1, len(self.energy)):
                soft_max_energy = self.capacity[t] * self.soft_max_charge_percentage / 100.0
                constraints.append(self.energy[t] <= soft_max_energy + self.overcharge_slack[t - 1])

        # Add soft minimum constraint (undercharge)
        if self.undercharge_slack is not None and self.soft_min_charge_percentage is not None:
            for t in range(1, len(self.energy)):
                soft_min_energy = self.capacity[t] * self.soft_min_charge_percentage / 100.0
                constraints.append(self.energy[t] >= soft_min_energy - self.undercharge_slack[t - 1])

        return constraints

    def cost(self) -> float:
        """Return the total cost including soft limit penalties."""
        cost = super().cost()

        # Add overcharge penalty cost
        if self.overcharge_slack is not None and self.overcharge_cost_values is not None:
            cost += lpSum(
                slack * cost_value
                for slack, cost_value in zip(self.overcharge_slack, self.overcharge_cost_values[1:], strict=False)
            )

        # Add undercharge penalty cost
        if self.undercharge_slack is not None and self.undercharge_cost_values is not None:
            cost += lpSum(
                slack * cost_value
                for slack, cost_value in zip(self.undercharge_slack, self.undercharge_cost_values[1:], strict=False)
            )

        return cost

    def get_outputs(self) -> Mapping[OutputName, OutputData]:
        """Return battery output specifications."""

        # Add the SOC sensor output
        energy_values = np.array(extract_values(self.energy))
        capacity_array = np.array(self.capacity)
        soc_values = (energy_values / capacity_array * 100.0).tolist()

        return {
            **super().get_outputs(),
            OUTPUT_NAME_BATTERY_STATE_OF_CHARGE: OutputData(
                type=OUTPUT_TYPE_SOC,
                unit="%",
                values=tuple(soc_values),
            ),
        }
