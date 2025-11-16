"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from pulp import LpAffineExpression, LpConstraint, LpVariable, lpSum

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


@dataclass
class BatterySection:
    """Represents a battery SOC section with cumulative energy variables."""

    name: str
    lower_percentage: float
    upper_percentage: float
    virtual_capacity: list[float]
    energy_charged: list[LpVariable | LpAffineExpression]
    energy_discharged: list[LpVariable | LpAffineExpression]
    charge_cost: list[float]
    discharge_cost: list[float]


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
        min_charge_percentage: float = 10,
        max_charge_percentage: float = 90,
        max_charge_power: Sequence[float] | float | None = None,
        max_discharge_power: Sequence[float] | float | None = None,
        efficiency: float = 99.0,
        early_charge_incentive: float = 1e-3,
        discharge_cost: float | None = None,
        undercharge_percentage: float | None = None,
        overcharge_percentage: float | None = None,
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
                to prefer later charging. Linearly increases from 0 to -incentive across periods.
                Default 0.001 (0.1 cents/kWh) encourages charging later when costs are equal.
            discharge_cost: Cost in $/kWh when discharging (applies to normal section)
            undercharge_percentage: Absolute minimum charge percentage (outer bound) 0-100
            overcharge_percentage: Absolute maximum charge percentage (outer bound) 0-100
            undercharge_cost: Cost in $/kWh for discharging in undercharge section
            overcharge_cost: Cost in $/kWh for charging in overcharge section

        Raises:
            ValueError: If percentage parameters violate ordering constraints

        """
        super().__init__(name=name, period=period, n_periods=n_periods)

        # Validate percentage ordering
        self._validate_percentages(
            min_charge_percentage,
            max_charge_percentage,
            undercharge_percentage,
            overcharge_percentage,
        )

        # Broadcast capacity to n_periods
        self.capacity: list[float] = broadcast_to_sequence(capacity, n_periods)

        # Broadcast initial_charge_percentage and get first value
        initial_soc_values = broadcast_to_sequence(initial_charge_percentage, n_periods)
        initial_soc_value: float = initial_soc_values[0]

        # Store battery-specific attributes
        self.efficiency = efficiency / 100.0  # Convert percentage to fraction
        self.min_charge_percentage = min_charge_percentage
        self.max_charge_percentage = max_charge_percentage
        self.undercharge_percentage = undercharge_percentage
        self.overcharge_percentage = overcharge_percentage

        # Broadcast costs
        capacity_array = np.array(self.capacity)
        normal_discharge_cost_array = (
            np.broadcast_to(np.atleast_1d(discharge_cost), (n_periods,))
            if discharge_cost is not None
            else np.zeros(n_periods)
        )
        undercharge_cost_array = (
            np.broadcast_to(np.atleast_1d(undercharge_cost), (n_periods,))
            if undercharge_cost is not None
            else np.zeros(n_periods)
        )
        overcharge_cost_array = (
            np.broadcast_to(np.atleast_1d(overcharge_cost), (n_periods,))
            if overcharge_cost is not None
            else np.zeros(n_periods)
        )

        # Broadcast charge/discharge power bounds
        charge_bounds: list[float] | None = broadcast_to_sequence(max_charge_power, n_periods)
        discharge_bounds: list[float] | None = broadcast_to_sequence(max_discharge_power, n_periods)

        # Power variables (bounds will be added as constraints)
        self.power_consumption = [
            LpVariable(name=f"{name}_power_consumption_{i}", lowBound=0) for i in range(n_periods)
        ]
        self.power_production = [LpVariable(name=f"{name}_power_production_{i}", lowBound=0) for i in range(n_periods)]

        # Build sections based on configuration
        self.sections = self._build_sections(
            name,
            n_periods,
            capacity_array,
            initial_soc_value,
            min_charge_percentage,
            max_charge_percentage,
            undercharge_percentage,
            overcharge_percentage,
            normal_discharge_cost_array,
            undercharge_cost_array,
            overcharge_cost_array,
            early_charge_incentive,
        )

        # Store prices for output (not used in cost calculation anymore)
        self.price_production: list[float] | None = broadcast_to_sequence(discharge_cost, n_periods)
        self.price_consumption: list[float] = np.linspace(0, -early_charge_incentive, n_periods).tolist()

        # Build section constraints
        self._build_section_constraints()

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

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the battery using multi-section approach."""
        costs: list[LpAffineExpression] = []

        # Sum costs from all sections
        for section in self.sections:
            # Cost for charging this section
            for t in range(1, self.n_periods):
                charge_energy = section.energy_charged[t] - section.energy_charged[t - 1]
                costs.append(charge_energy * section.charge_cost[t])

                # Cost for discharging this section
                discharge_energy = section.energy_discharged[t] - section.energy_discharged[t - 1]
                costs.append(discharge_energy * section.discharge_cost[t])

        return costs

    def outputs(self) -> Mapping[OutputName, OutputData]:
        """Return battery output specifications."""
        # Calculate total SOC from all sections
        total_energy_values = []
        for t in range(self.n_periods):
            total_energy = 0.0
            for section in self.sections:
                section_energy_charged = extract_values([section.energy_charged[t]])[0]
                section_energy_discharged = extract_values([section.energy_discharged[t]])[0]
                total_energy += section_energy_charged - section_energy_discharged
            total_energy_values.append(total_energy)

        # Convert to SOC percentage
        capacity_array = np.array(self.capacity)
        soc_values = (np.array(total_energy_values) / capacity_array * 100.0).tolist()

        outputs: dict[OutputName, OutputData] = {
            OUTPUT_NAME_POWER_CONSUMED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_consumption)
            ),
            OUTPUT_NAME_POWER_PRODUCED: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=extract_values(self.power_production)
            ),
            OUTPUT_NAME_ENERGY_STORED: OutputData(
                type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(total_energy_values)
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

    @staticmethod
    def _validate_percentages(
        min_charge: float,
        max_charge: float,
        undercharge: float | None,
        overcharge: float | None,
    ) -> None:
        """Validate that percentage parameters follow logical ordering.

        Args:
            min_charge: Minimum (preferred) charge percentage
            max_charge: Maximum (preferred) charge percentage
            undercharge: Undercharge (absolute minimum) percentage
            overcharge: Overcharge (absolute maximum) percentage

        Raises:
            ValueError: If ordering constraints are violated

        """
        if min_charge >= max_charge:
            msg = (
                f"min_charge_percentage ({min_charge}) must be less than "
                f"max_charge_percentage ({max_charge})"
            )
            raise ValueError(msg)

        if undercharge is not None and undercharge >= min_charge:
            msg = (
                f"undercharge_percentage ({undercharge}) must be less than "
                f"min_charge_percentage ({min_charge})"
            )
            raise ValueError(msg)

        if overcharge is not None and overcharge <= max_charge:
            msg = (
                f"overcharge_percentage ({overcharge}) must be greater than "
                f"max_charge_percentage ({max_charge})"
            )
            raise ValueError(msg)

    def _build_sections(
        self,
        name: str,
        n_periods: int,
        capacity_array: np.ndarray,
        initial_soc_value: float,
        min_charge_percentage: float,
        max_charge_percentage: float,
        undercharge_percentage: float | None,
        overcharge_percentage: float | None,
        normal_discharge_cost_array: np.ndarray,
        undercharge_cost_array: np.ndarray,
        overcharge_cost_array: np.ndarray,
        early_charge_incentive: float,
    ) -> list[BatterySection]:
        """Build battery sections based on configuration.

        Returns:
            List of BatterySection objects

        """
        sections: list[BatterySection] = []

        # Calculate early charge incentive array (negative values encourage later charging)
        incentive_array = np.linspace(0, -early_charge_incentive, n_periods)

        # Build sections from lowest to highest SOC
        section_boundaries: list[tuple[float, float, str]] = []

        # Always create undercharge section if needed (below min)
        if undercharge_percentage is not None:
            section_boundaries.append((undercharge_percentage, min_charge_percentage, "undercharge"))

        # Normal section: when no extra sections, spans full range with min/max as enforced bounds
        # When extra sections exist, spans only min-max range
        if undercharge_percentage is None and overcharge_percentage is None:
            # No extended ranges - normal section spans 0-100% with min/max enforced by capacity bounds
            section_boundaries.append((0.0, 100.0, "normal"))
        else:
            # Have extended ranges - normal section only spans preferred range
            section_boundaries.append((min_charge_percentage, max_charge_percentage, "normal"))

        # Always create overcharge section if needed (above max)
        if overcharge_percentage is not None:
            section_boundaries.append((max_charge_percentage, overcharge_percentage, "overcharge"))

        # Calculate initial energy distribution across sections
        initial_energy_per_section = self._distribute_initial_energy(
            initial_soc_value,
            capacity_array[0],
            section_boundaries,
        )

        # Create sections
        for (lower_pct, upper_pct, section_type), initial_energy in zip(
            section_boundaries, initial_energy_per_section, strict=True
        ):
            virtual_capacity = (capacity_array * (upper_pct - lower_pct) / 100.0).tolist()

            # Determine costs based on section type
            if section_type == "undercharge":
                charge_cost = incentive_array.copy()
                discharge_cost = undercharge_cost_array.copy()
            elif section_type == "normal":
                charge_cost = incentive_array.copy()
                discharge_cost = normal_discharge_cost_array.copy()
            else:  # overcharge
                charge_cost = overcharge_cost_array.copy()
                discharge_cost = normal_discharge_cost_array.copy()

            # Create energy variables
            energy_charged: list[LpVariable | LpAffineExpression] = [
                LpAffineExpression(constant=initial_energy),
                *[
                    LpVariable(
                        name=f"{name}_{section_type}_charged_{i}",
                        lowBound=0,
                        upBound=virtual_capacity[i],
                    )
                    for i in range(1, n_periods)
                ],
            ]

            energy_discharged: list[LpVariable | LpAffineExpression] = [
                LpAffineExpression(constant=0.0),
                *[
                    LpVariable(
                        name=f"{name}_{section_type}_discharged_{i}",
                        lowBound=0,
                        upBound=virtual_capacity[i],
                    )
                    for i in range(1, n_periods)
                ],
            ]

            sections.append(
                BatterySection(
                    name=section_type,
                    lower_percentage=lower_pct,
                    upper_percentage=upper_pct,
                    virtual_capacity=virtual_capacity,
                    energy_charged=energy_charged,
                    energy_discharged=energy_discharged,
                    charge_cost=charge_cost.tolist(),
                    discharge_cost=discharge_cost.tolist(),
                )
            )

        return sections

    @staticmethod
    def _distribute_initial_energy(
        initial_soc_percentage: float,
        capacity: float,
        section_boundaries: list[tuple[float, float, str]],
    ) -> list[float]:
        """Distribute initial energy across sections, filling from bottom up.

        Args:
            initial_soc_percentage: Initial SOC as percentage
            capacity: Battery capacity in kWh
            section_boundaries: List of (lower_pct, upper_pct, name) tuples

        Returns:
            List of initial energy values for each section

        """
        initial_energy_total = initial_soc_percentage * capacity / 100.0
        section_energies: list[float] = []

        remaining_energy = initial_energy_total
        for lower_pct, upper_pct, _ in section_boundaries:
            section_capacity = capacity * (upper_pct - lower_pct) / 100.0

            if remaining_energy >= section_capacity:
                # Fill this section completely
                section_energies.append(section_capacity)
                remaining_energy -= section_capacity
            elif remaining_energy > 0:
                # Partially fill this section
                section_energies.append(remaining_energy)
                remaining_energy = 0
            else:
                # No energy left for this section
                section_energies.append(0.0)

        return section_energies

    def _build_section_constraints(self) -> None:
        """Build all constraints for multi-section battery model."""
        constraints: list[LpConstraint] = []

        for t in range(1, self.n_periods):
            # 1. Monotonicity constraints (non-decreasing cumulative variables)
            for section in self.sections:
                constraints.append(section.energy_charged[t] >= section.energy_charged[t - 1])
                constraints.append(section.energy_discharged[t] >= section.energy_discharged[t - 1])

            # 2. Stacked SOC ordering constraints (higher sections only charged when lower are full)
            for i in range(len(self.sections) - 1):
                lower_section = self.sections[i]
                upper_section = self.sections[i + 1]

                # Lower section SOC >= Upper section SOC
                lower_soc = (lower_section.energy_charged[t] - lower_section.energy_discharged[t]) / (
                    lower_section.virtual_capacity[t] if lower_section.virtual_capacity[t] > 0 else 1.0
                )
                upper_soc = (upper_section.energy_charged[t] - upper_section.energy_discharged[t]) / (
                    upper_section.virtual_capacity[t] if upper_section.virtual_capacity[t] > 0 else 1.0
                )

                constraints.append(lower_soc >= upper_soc)

            # 3. Power transfer consistency constraint
            # Sum of net energy changes across all sections = net power input * period
            total_energy_change = lpSum(
                (section.energy_charged[t] - section.energy_charged[t - 1])
                - (section.energy_discharged[t] - section.energy_discharged[t - 1])
                for section in self.sections
            )

            net_power_input = (
                self.power_consumption[t - 1] * self.efficiency - self.power_production[t - 1] / self.efficiency
            )

            constraints.append(total_energy_change == net_power_input * self.period)

        # 4. Section capacity constraints
        for section in self.sections:
            for t in range(self.n_periods):
                net_energy = section.energy_charged[t] - section.energy_discharged[t]
                constraints.append(net_energy >= 0)
                constraints.append(net_energy <= section.virtual_capacity[t])

        # 5. Min/max SOC enforcement for normal section when no extended sections
        if len(self.sections) == 1:  # Only normal section
            normal_section = self.sections[0]
            capacity_array = np.array(self.capacity)
            min_energy_array = capacity_array * (self.min_charge_percentage / 100.0)
            max_energy_array = capacity_array * (self.max_charge_percentage / 100.0)

            for t in range(self.n_periods):
                net_energy = normal_section.energy_charged[t] - normal_section.energy_discharged[t]
                constraints.append(net_energy >= min_energy_array[t])
                constraints.append(net_energy <= max_energy_array[t])

        # Store constraints with appropriate names
        self._constraints[CONSTRAINT_NAME_ENERGY_BALANCE] = constraints

