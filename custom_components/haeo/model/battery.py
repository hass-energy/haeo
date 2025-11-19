"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence

import numpy as np
from pulp import LpAffineExpression, LpVariable
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
        """Initialize a battery section.

        Args:
            name: Name of the section
            capacity: Section capacity in kWh per period
            charge_cost: Cost in $/kWh for charging per period
            discharge_cost: Cost in $/kWh for discharging per period
            initial_charge: Initial charge in kWh
            period: Time period in hours
            n_periods: Number of time periods

        """
        self.name = name
        self.capacity = capacity
        self.charge_cost = [LpAffineExpression(constant=float(c)) for c in charge_cost]
        self.discharge_cost = [LpAffineExpression(constant=float(c)) for c in discharge_cost]
        self.period = period
        self.n_periods = n_periods

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

        # These parameters are defined per power item (so n_periods values)
        self.efficiency = broadcast_to_sequence(efficiency, n_periods)
        self.max_charge_power = broadcast_to_sequence(max_charge_power, n_periods)
        self.max_discharge_power = broadcast_to_sequence(max_discharge_power, n_periods)
        undercharge_cost = broadcast_to_sequence(undercharge_cost, n_periods)
        overcharge_cost = broadcast_to_sequence(overcharge_cost, n_periods)
        discharge_cost = broadcast_to_sequence(discharge_cost, n_periods)

        # These parameters are defined per energy item, so extend by 1 (repeats the last value)
        min_charge_ratio = broadcast_to_sequence(min_charge_percentage, n_periods + 1)
        max_charge_ratio = broadcast_to_sequence(max_charge_percentage, n_periods + 1)
        undercharge_ratio = broadcast_to_sequence(undercharge_percentage, n_periods + 1)
        overcharge_ratio = broadcast_to_sequence(overcharge_percentage, n_periods + 1)
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)

        # Validate percentage ordering for all time periods
        self._validate_parameters(
            min_charge_ratio, max_charge_ratio, undercharge_ratio, overcharge_ratio, undercharge_cost, overcharge_cost
        )

        # Get the first value of initial_charge_percentage and convert to energy
        initial_soc_ratio = broadcast_to_sequence(initial_charge_percentage, n_periods)[0] / 100.0

        # From the early charge value, make two incentives, one for charging early and one for discharging early.
        # We will also multiply these values for each section to make it more/less attractive.
        # This also makes a small spread between charging and discharging which helps prevent oscillation.
        charge_early_incentive = np.linspace(-early_charge_incentive, 0.0, n_periods)
        discharge_early_incentive = np.linspace(0.0, early_charge_incentive, n_periods)

        # Convert cost parameters to sequences (per power item so n_periods)

        # This is the energy that is unusable due to being below absolute minimum percentage
        unusable_ratio = undercharge_ratio if undercharge_ratio is not None else min_charge_ratio
        self.inaccessible_energy: Sequence[float] = (np.array(unusable_ratio) * np.array(self.capacity)).tolist()

        # Calculate initial charge in kWh (remove unusable percentage)
        initial_charge: float = max((initial_soc_ratio - unusable_ratio[0]) * self.capacity[0], 0.0)

        self._sections: list[BatterySection] = []
        if undercharge_ratio is not None and undercharge_cost is not None:
            undercharge_range = np.array(min_charge_ratio) - np.array(undercharge_ratio)
            undercharge_capacity = (undercharge_range * np.array(self.capacity)).tolist()
            self._sections.append(
                BatterySection(
                    name="undercharge",
                    capacity=undercharge_capacity,
                    charge_cost=(charge_early_incentive * 3).tolist(),
                    discharge_cost=((discharge_early_incentive * 1) + np.array(discharge_cost)).tolist(),
                    initial_charge=initial_charge,
                    period=period,
                    n_periods=n_periods,
                )
            )
            initial_charge = max(initial_charge - undercharge_capacity[0], 0.0)

        normal_range = (np.array(max_charge_percentage) - np.array(min_charge_percentage)) / 100.0
        normal_capacity = (normal_range * np.array(self.capacity)).tolist()
        self._sections.append(
            BatterySection(
                name="normal",
                capacity=normal_capacity,
                charge_cost=(charge_early_incentive * 2).tolist(),
                discharge_cost=((discharge_early_incentive * 2) + np.array(discharge_cost)).tolist(),
                initial_charge=initial_charge,
                period=period,
                n_periods=n_periods,
            )
        )
        initial_charge = max(initial_charge - normal_capacity[0], 0.0)

        if overcharge_ratio is not None and overcharge_cost is not None:
            overcharge_range = np.array(overcharge_ratio) - np.array(max_charge_ratio)
            overcharge_capacity = (overcharge_range * np.array(self.capacity)).tolist()
            self._sections.append(
                BatterySection(
                    name="overcharge",
                    capacity=overcharge_capacity,
                    charge_cost=((charge_early_incentive * 1) + np.array(overcharge_cost)).tolist(),
                    discharge_cost=((discharge_early_incentive * 3) + np.array(discharge_cost)).tolist(),
                    initial_charge=initial_charge,
                    period=period,
                    n_periods=n_periods,
                )
            )

        # Add section constraints to battery constraints
        for section in self._sections:
            for constraint_name, constraint in section.constraints.items():
                self._constraints[f"{section.name}_{constraint_name}"] = constraint

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
        return [lpSum(s.power_consumption[t] for s in self._sections) for t in range(self.n_periods)]

    @property
    def power_production(self) -> Sequence[LpAffineExpression]:
        """Return the power production of the battery."""
        return [lpSum(s.power_production[t] for s in self._sections) for t in range(self.n_periods)]

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
                (s.energy_in[t + 1] - s.energy_in[t]) - (s.energy_out[t + 1] - s.energy_out[t]) for s in self._sections
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
        # Get total energy stored values
        total_energy_values = extract_values(self.stored_energy)

        # Convert to SOC percentage
        capacity_array = np.array(self.capacity)[:-1]  # Use n_periods values
        soc_values = (np.array(total_energy_values) / capacity_array * 100.0).tolist()

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(self.power_consumption))
            ),
            OUTPUT_NAME_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(self.power_production))
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

        for section in self._sections:
            # Section stored_energy has n_periods+1 values, we only want n_periods for outputs
            section_energy_values = extract_values(section.stored_energy)[:-1]
            section_outputs: dict[OutputName, OutputData] = {
                f"{section.name}_{OUTPUT_NAME_ENERGY_STORED}": OutputData(  # type: ignore[dict-item]
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(section_energy_values)
                ),
                f"{section.name}_{OUTPUT_NAME_POWER_PRODUCED}": OutputData(  # type: ignore[dict-item]
                    type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(section.power_production))
                ),
                f"{section.name}_{OUTPUT_NAME_POWER_CONSUMED}": OutputData(  # type: ignore[dict-item]
                    type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(section.power_consumption))
                ),
                f"{section.name}_{OUTPUT_NAME_PRICE_CONSUMPTION}": OutputData(  # type: ignore[dict-item]
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=tuple(extract_values(section.charge_cost))
                ),
                f"{section.name}_{OUTPUT_NAME_PRICE_PRODUCTION}": OutputData(  # type: ignore[dict-item]
                    type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=tuple(extract_values(section.discharge_cost))
                ),
            }
            outputs.update(section_outputs)

        return outputs

    @staticmethod
    def _validate_parameters(
        min_charge_ratio: Sequence[float],
        max_charge_ratio: Sequence[float],
        undercharge_ratio: Sequence[float] | None,
        overcharge_ratio: Sequence[float] | None,
        undercharge_cost: Sequence[float] | float | None,
        overcharge_cost: Sequence[float] | float | None,
    ) -> None:
        """Validate percentage ordering for all time periods.

        Args:
            min_charge_ratio: Minimum charge percentage sequence
            max_charge_ratio: Maximum charge percentage sequence
            undercharge_ratio: Undercharge ratio sequence or None
            overcharge_ratio: Overcharge ratio sequence or None
            undercharge_cost: Undercharge cost or None
            overcharge_cost: Overcharge cost or None

        Raises:
            ValueError: If percentage parameters violate ordering constraints

        """
        # If undercharge_percentage is not None, then undercharge_cost must be provided
        if undercharge_ratio is not None and undercharge_cost is None:
            msg = "undercharge_cost must be provided if undercharge_percentage is not None"
            raise ValueError(msg)

        # If overcharge_percentage is not None, then overcharge_cost must be provided
        if overcharge_ratio is not None and overcharge_cost is None:
            msg = "overcharge_cost must be provided if overcharge_percentage is not None"
            raise ValueError(msg)

        # Validate min < max for all time periods
        for t in range(len(min_charge_ratio)):
            if min_charge_ratio[t] >= max_charge_ratio[t]:
                msg = (
                    f"min_charge_ratio ({min_charge_ratio[t]}) "
                    f"must be less than max_charge_ratio ({max_charge_ratio[t]}) "
                    f"at time period {t}"
                )
                raise ValueError(msg)

        # Validate undercharge < min for all time periods
        if undercharge_ratio is not None:
            for t in range(len(undercharge_ratio)):
                if undercharge_ratio[t] >= min_charge_ratio[t]:
                    msg = (
                        f"undercharge_ratio ({undercharge_ratio[t]}) "
                        f"must be less than min_charge_ratio ({min_charge_ratio[t]}) "
                        f"at time period {t}"
                    )
                    raise ValueError(msg)

        # Validate max < overcharge for all time periods
        if overcharge_ratio is not None:
            for t in range(len(overcharge_ratio)):
                if max_charge_ratio[t] >= overcharge_ratio[t]:
                    msg = (
                        f"overcharge_ratio ({overcharge_ratio[t]}) "
                        f"must be greater than max_charge_ratio ({max_charge_ratio[t]}) "
                        f"at time period {t}"
                    )
                    raise ValueError(msg)
