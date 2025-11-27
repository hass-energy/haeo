"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

import numpy as np
from pulp import LpAffineExpression, LpVariable
from pulp.pulp import lpSum

from .const import (
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
    OUTPUT_TYPE_SOC,
    OutputData,
)
from .element import Element
from .util import broadcast_to_sequence, extract_values, percentage_to_ratio

# Battery section names
BATTERY_SECTION_UNDERCHARGE: Final = "undercharge"
BATTERY_SECTION_NORMAL: Final = "normal"
BATTERY_SECTION_OVERCHARGE: Final = "overcharge"

# Battery constraint names (also used as shadow price output names)
BATTERY_POWER_BALANCE: Final = "battery_power_balance"
BATTERY_ENERGY_BALANCE: Final = "battery_energy_balance"
BATTERY_MAX_CHARGE_POWER: Final = "battery_max_charge_power"
BATTERY_MAX_DISCHARGE_POWER: Final = "battery_max_discharge_power"
BATTERY_SOC_MIN: Final = "battery_soc_min"
BATTERY_SOC_MAX: Final = "battery_soc_max"
BATTERY_TIME_SLICE: Final = "battery_time_slice"

# Internal section constraint name patterns (used to build shadow price outputs)
BATTERY_MONOTONIC_CHARGE: Final = "monotonic_charge"
BATTERY_MONOTONIC_DISCHARGE: Final = "monotonic_discharge"
BATTERY_CAPACITY_UPPER: Final = "capacity_upper"
BATTERY_CAPACITY_LOWER: Final = "capacity_lower"

# Battery output names
BATTERY_POWER_CHARGE: Final = "battery_power_charge"
BATTERY_POWER_DISCHARGE: Final = "battery_power_discharge"
BATTERY_ENERGY_STORED: Final = "battery_energy_stored"
BATTERY_STATE_OF_CHARGE: Final = "battery_state_of_charge"
BATTERY_CHARGE_PRICE: Final = "battery_charge_price"
BATTERY_DISCHARGE_PRICE: Final = "battery_discharge_price"

# Section-specific output names
BATTERY_UNDERCHARGE_ENERGY_STORED: Final = "battery_undercharge_energy_stored"
BATTERY_UNDERCHARGE_POWER_CHARGE: Final = "battery_undercharge_power_charge"
BATTERY_UNDERCHARGE_POWER_DISCHARGE: Final = "battery_undercharge_power_discharge"
BATTERY_UNDERCHARGE_CHARGE_PRICE: Final = "battery_undercharge_charge_price"
BATTERY_UNDERCHARGE_DISCHARGE_PRICE: Final = "battery_undercharge_discharge_price"
BATTERY_UNDERCHARGE_MONOTONIC_CHARGE: Final = "battery_undercharge_monotonic_charge"
BATTERY_UNDERCHARGE_MONOTONIC_DISCHARGE: Final = "battery_undercharge_monotonic_discharge"
BATTERY_UNDERCHARGE_CAPACITY_UPPER: Final = "battery_undercharge_capacity_upper"
BATTERY_UNDERCHARGE_CAPACITY_LOWER: Final = "battery_undercharge_capacity_lower"

BATTERY_NORMAL_ENERGY_STORED: Final = "battery_normal_energy_stored"
BATTERY_NORMAL_POWER_CHARGE: Final = "battery_normal_power_charge"
BATTERY_NORMAL_POWER_DISCHARGE: Final = "battery_normal_power_discharge"
BATTERY_NORMAL_CHARGE_PRICE: Final = "battery_normal_charge_price"
BATTERY_NORMAL_DISCHARGE_PRICE: Final = "battery_normal_discharge_price"
BATTERY_NORMAL_MONOTONIC_CHARGE: Final = "battery_normal_monotonic_charge"
BATTERY_NORMAL_MONOTONIC_DISCHARGE: Final = "battery_normal_monotonic_discharge"
BATTERY_NORMAL_CAPACITY_UPPER: Final = "battery_normal_capacity_upper"
BATTERY_NORMAL_CAPACITY_LOWER: Final = "battery_normal_capacity_lower"

BATTERY_OVERCHARGE_ENERGY_STORED: Final = "battery_overcharge_energy_stored"
BATTERY_OVERCHARGE_POWER_CHARGE: Final = "battery_overcharge_power_charge"
BATTERY_OVERCHARGE_POWER_DISCHARGE: Final = "battery_overcharge_power_discharge"
BATTERY_OVERCHARGE_CHARGE_PRICE: Final = "battery_overcharge_charge_price"
BATTERY_OVERCHARGE_DISCHARGE_PRICE: Final = "battery_overcharge_discharge_price"
BATTERY_OVERCHARGE_MONOTONIC_CHARGE: Final = "battery_overcharge_monotonic_charge"
BATTERY_OVERCHARGE_MONOTONIC_DISCHARGE: Final = "battery_overcharge_monotonic_discharge"
BATTERY_OVERCHARGE_CAPACITY_UPPER: Final = "battery_overcharge_capacity_upper"
BATTERY_OVERCHARGE_CAPACITY_LOWER: Final = "battery_overcharge_capacity_lower"

# Type for battery constraint names (includes all internal and external constraints)
type BatteryConstraintName = Literal[
    "battery_power_balance",
    "battery_energy_balance",
    "battery_max_charge_power",
    "battery_max_discharge_power",
    "battery_soc_min",
    "battery_soc_max",
    "battery_time_slice",
    "battery_undercharge_monotonic_charge",
    "battery_undercharge_monotonic_discharge",
    "battery_undercharge_capacity_upper",
    "battery_undercharge_capacity_lower",
    "battery_normal_monotonic_charge",
    "battery_normal_monotonic_discharge",
    "battery_normal_capacity_upper",
    "battery_normal_capacity_lower",
    "battery_overcharge_monotonic_charge",
    "battery_overcharge_monotonic_discharge",
    "battery_overcharge_capacity_upper",
    "battery_overcharge_capacity_lower",
]

# Type for all battery output names (union of base outputs and constraints)
type BatteryOutputName = (
    Literal[
        "battery_power_charge",
        "battery_power_discharge",
        "battery_energy_stored",
        "battery_state_of_charge",
        "battery_charge_price",
        "battery_discharge_price",
        "battery_undercharge_energy_stored",
        "battery_undercharge_power_charge",
        "battery_undercharge_power_discharge",
        "battery_undercharge_charge_price",
        "battery_undercharge_discharge_price",
        "battery_normal_energy_stored",
        "battery_normal_power_charge",
        "battery_normal_power_discharge",
        "battery_normal_charge_price",
        "battery_normal_discharge_price",
        "battery_overcharge_energy_stored",
        "battery_overcharge_power_charge",
        "battery_overcharge_power_discharge",
        "battery_overcharge_charge_price",
        "battery_overcharge_discharge_price",
    ]
    | BatteryConstraintName
)

# Set of battery output names for runtime validation and type narrowing
# Note: Includes dynamic constraint names built from sections, so type is inferred
BATTERY_OUTPUT_NAMES: Final[frozenset[BatteryOutputName]] = frozenset(
    (
        BATTERY_POWER_CHARGE,
        BATTERY_POWER_DISCHARGE,
        BATTERY_ENERGY_STORED,
        BATTERY_STATE_OF_CHARGE,
        BATTERY_CHARGE_PRICE,
        BATTERY_DISCHARGE_PRICE,
        BATTERY_UNDERCHARGE_ENERGY_STORED,
        BATTERY_UNDERCHARGE_POWER_CHARGE,
        BATTERY_UNDERCHARGE_POWER_DISCHARGE,
        BATTERY_UNDERCHARGE_CHARGE_PRICE,
        BATTERY_UNDERCHARGE_DISCHARGE_PRICE,
        BATTERY_NORMAL_ENERGY_STORED,
        BATTERY_NORMAL_POWER_CHARGE,
        BATTERY_NORMAL_POWER_DISCHARGE,
        BATTERY_NORMAL_CHARGE_PRICE,
        BATTERY_NORMAL_DISCHARGE_PRICE,
        BATTERY_OVERCHARGE_ENERGY_STORED,
        BATTERY_OVERCHARGE_POWER_CHARGE,
        BATTERY_OVERCHARGE_POWER_DISCHARGE,
        BATTERY_OVERCHARGE_CHARGE_PRICE,
        BATTERY_OVERCHARGE_DISCHARGE_PRICE,
        BATTERY_POWER_BALANCE,
        BATTERY_ENERGY_BALANCE,
        BATTERY_MAX_CHARGE_POWER,
        BATTERY_MAX_DISCHARGE_POWER,
        BATTERY_SOC_MIN,
        BATTERY_SOC_MAX,
        BATTERY_TIME_SLICE,
        BATTERY_UNDERCHARGE_MONOTONIC_CHARGE,
        BATTERY_UNDERCHARGE_MONOTONIC_DISCHARGE,
        BATTERY_UNDERCHARGE_CAPACITY_UPPER,
        BATTERY_UNDERCHARGE_CAPACITY_LOWER,
        BATTERY_NORMAL_MONOTONIC_CHARGE,
        BATTERY_NORMAL_MONOTONIC_DISCHARGE,
        BATTERY_NORMAL_CAPACITY_UPPER,
        BATTERY_NORMAL_CAPACITY_LOWER,
        BATTERY_OVERCHARGE_MONOTONIC_CHARGE,
        BATTERY_OVERCHARGE_MONOTONIC_DISCHARGE,
        BATTERY_OVERCHARGE_CAPACITY_UPPER,
        BATTERY_OVERCHARGE_CAPACITY_LOWER,
    )
)


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
            BATTERY_MONOTONIC_CHARGE: [self.energy_in[t + 1] >= self.energy_in[t] for t in range(n_periods)],
            BATTERY_MONOTONIC_DISCHARGE: [self.energy_out[t + 1] >= self.energy_out[t] for t in range(n_periods)],
            BATTERY_CAPACITY_UPPER: [
                self.energy_in[t + 1] - self.energy_out[t + 1] <= capacity[t + 1] for t in range(n_periods)
            ],
            BATTERY_CAPACITY_LOWER: [self.energy_in[t + 1] - self.energy_out[t + 1] >= 0 for t in range(n_periods)],
        }

        # Pre-calculate power and energy expressions to avoid recomputing them
        self.power_consumption: Sequence[LpAffineExpression] = [
            (self.energy_in[t + 1] - self.energy_in[t]) / self.period for t in range(self.n_periods)
        ]
        self.power_production: Sequence[LpAffineExpression] = [
            (self.energy_out[t + 1] - self.energy_out[t]) / self.period for t in range(self.n_periods)
        ]
        self.stored_energy: Sequence[LpAffineExpression] = [
            self.energy_in[t] - self.energy_out[t] for t in range(self.n_periods + 1)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost of the section."""
        return [
            *[(self.energy_in[t + 1] - self.energy_in[t]) * self.charge_cost[t] for t in range(self.n_periods)],
            *[(self.energy_out[t + 1] - self.energy_out[t]) * self.discharge_cost[t] for t in range(self.n_periods)],
        ]


class Battery(Element[BatteryOutputName, BatteryConstraintName]):
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
            efficiency: Battery round-trip efficiency percentage 0-100.
                Internally converted to one-way efficiency (sqrt of round-trip) and applied
                symmetrically to charge and discharge operations.
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

        # Convert round-trip efficiency to one-way efficiency (applied symmetrically to charge/discharge)
        # Round-trip efficiency = (one-way efficiency)^2, so one-way = sqrt(round-trip)
        efficiency_ratio = percentage_to_ratio(broadcast_to_sequence(efficiency, n_periods))
        self.efficiency = [np.sqrt(eff) for eff in efficiency_ratio]
        self.max_charge_power = broadcast_to_sequence(max_charge_power, n_periods)
        self.max_discharge_power = broadcast_to_sequence(max_discharge_power, n_periods)
        undercharge_cost = broadcast_to_sequence(undercharge_cost, n_periods)
        overcharge_cost = broadcast_to_sequence(overcharge_cost, n_periods)
        discharge_cost = broadcast_to_sequence(discharge_cost if discharge_cost is not None else 0.0, n_periods)

        # These parameters are defined per energy item, so extend by 1 (repeats the last value)
        # Convert percentages (0-100) to ratios (0-1)
        min_charge_ratio = percentage_to_ratio(broadcast_to_sequence(min_charge_percentage, n_periods + 1))
        max_charge_ratio = percentage_to_ratio(broadcast_to_sequence(max_charge_percentage, n_periods + 1))
        undercharge_ratio = percentage_to_ratio(broadcast_to_sequence(undercharge_percentage, n_periods + 1))
        overcharge_ratio = percentage_to_ratio(broadcast_to_sequence(overcharge_percentage, n_periods + 1))
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)

        # Validate percentage ordering for all time periods
        self._validate_parameters(
            min_charge_ratio, max_charge_ratio, undercharge_ratio, overcharge_ratio, undercharge_cost, overcharge_cost
        )

        # Get the first value of initial_charge_percentage and convert to energy
        initial_soc_ratio = broadcast_to_sequence(initial_charge_percentage, n_periods)[0] / 100.0

        # From the early charge value, make two incentives, one for charging early and one for discharging early.
        # We will also multiply these values for each section to make it more/less attractive.
        # Charge incentive: negative cost (benefit) that decreases over time (-incentive -> 0)
        #   This provides a small benefit for charging earlier when costs are equal.
        # Discharge incentive: positive cost that increases over time (incentive -> 2*incentive)
        #   This increases the cost of discharging earlier, encouraging later discharge when revenues are equal.
        charge_early_incentive = np.linspace(-early_charge_incentive, 0.0, n_periods)
        discharge_early_incentive = np.linspace(early_charge_incentive, 2.0 * early_charge_incentive, n_periods)

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
            # Only allocate up to the section's capacity
            section_initial_charge = min(initial_charge, undercharge_capacity[0])
            self._sections.append(
                BatterySection(
                    name=BATTERY_SECTION_UNDERCHARGE,
                    capacity=undercharge_capacity,
                    charge_cost=(charge_early_incentive * 3).tolist(),
                    discharge_cost=((discharge_early_incentive * 1) + np.array(undercharge_cost)).tolist(),
                    initial_charge=section_initial_charge,
                    period=period,
                    n_periods=n_periods,
                )
            )
            initial_charge = max(initial_charge - section_initial_charge, 0.0)

        normal_range = np.array(max_charge_ratio) - np.array(min_charge_ratio)
        normal_capacity = (normal_range * np.array(self.capacity)).tolist()
        # Only allocate up to the section's capacity
        section_initial_charge = min(initial_charge, normal_capacity[0])
        self._sections.append(
            BatterySection(
                name=BATTERY_SECTION_NORMAL,
                capacity=normal_capacity,
                charge_cost=(charge_early_incentive * 2).tolist(),
                discharge_cost=((discharge_early_incentive * 2) + np.array(discharge_cost)).tolist(),
                initial_charge=section_initial_charge,
                period=period,
                n_periods=n_periods,
            )
        )
        initial_charge = max(initial_charge - section_initial_charge, 0.0)

        if overcharge_ratio is not None and overcharge_cost is not None:
            overcharge_range = np.array(overcharge_ratio) - np.array(max_charge_ratio)
            overcharge_capacity = (overcharge_range * np.array(self.capacity)).tolist()
            # Only allocate up to the section's capacity
            section_initial_charge = min(initial_charge, overcharge_capacity[0])
            self._sections.append(
                BatterySection(
                    name=BATTERY_SECTION_OVERCHARGE,
                    capacity=overcharge_capacity,
                    charge_cost=((charge_early_incentive * 1) + np.array(overcharge_cost)).tolist(),
                    discharge_cost=((discharge_early_incentive * 3) + np.array(discharge_cost)).tolist(),
                    initial_charge=section_initial_charge,
                    period=period,
                    n_periods=n_periods,
                )
            )

        # Add section constraints to battery constraints
        for section in self._sections:
            for constraint_name, constraint in section.constraints.items():
                # Cast to BatteryConstraintName since f-strings create str type
                key: BatteryConstraintName = f"{section.name}_{constraint_name}"  # type: ignore[assignment]
                self._constraints[key] = constraint

        # Pre-calculate power and energy expressions to avoid recomputing them
        # power_consumption: external power drawn from network (more than stored due to efficiency loss)
        # power_production: external power sent to network (less than released due to efficiency loss)
        self.power_consumption: Sequence[LpAffineExpression] = [
            lpSum(s.power_consumption[t] for s in self._sections) / self.efficiency[t] for t in range(self.n_periods)
        ]
        self.power_production: Sequence[LpAffineExpression] = [
            lpSum(s.power_production[t] for s in self._sections) * self.efficiency[t] for t in range(self.n_periods)
        ]
        self.stored_energy: Sequence[LpAffineExpression] = [
            self.inaccessible_energy[t] + lpSum(s.energy_in[t] - s.energy_out[t] for s in self._sections)
            for t in range(self.n_periods + 1)
        ]

        # Power limits constrain external power (power_consumption/power_production already include efficiency)
        if self.max_charge_power is not None:
            self._constraints[BATTERY_MAX_CHARGE_POWER] = [
                self.power_consumption[t] <= self.max_charge_power[t] for t in range(self.n_periods)
            ]
        if self.max_discharge_power is not None:
            self._constraints[BATTERY_MAX_DISCHARGE_POWER] = [
                self.power_production[t] <= self.max_discharge_power[t] for t in range(self.n_periods)
            ]

        # Prevent simultaneous full charging and discharging using time-slicing constraint:
        # This allows cycling but on a time-sliced basis (e.g., charge 50% of time, discharge 50%)
        if self.max_charge_power is not None and self.max_discharge_power is not None:
            self._constraints[BATTERY_TIME_SLICE] = [
                self.power_consumption[t] / self.max_charge_power[t]
                + self.power_production[t] / self.max_discharge_power[t]
                <= 1.0
                for t in range(self.n_periods)
                if self.max_charge_power[t] > 0 and self.max_discharge_power[t] > 0
            ]

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        Efficiency losses are applied to prevent oscillation (cycling).
        """

        # Power balance: connection_power equals net external power
        # power_consumption and power_production already include efficiency losses
        self._constraints[BATTERY_POWER_BALANCE] = [
            self.connection_power(t) == self.power_consumption[t] - self.power_production[t]
            for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the battery using multi-section approach."""
        costs: list[LpAffineExpression] = []

        # Sum costs from all sections
        for s in self._sections:
            costs.extend(s.cost())

        return costs

    def outputs(self) -> Mapping[BatteryOutputName, OutputData]:
        """Return battery output specifications."""
        # Get total energy stored values
        total_energy_values = extract_values(self.stored_energy)

        # Convert to SOC percentage
        capacity_array = np.array(self.capacity)
        soc_values = (np.array(total_energy_values) / capacity_array * 100.0).tolist()

        outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_POWER_CHARGE: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(self.power_consumption)), direction="-"
            ),
            BATTERY_POWER_DISCHARGE: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=tuple(extract_values(self.power_production)), direction="+"
            ),
            BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(total_energy_values)),
            BATTERY_STATE_OF_CHARGE: OutputData(
                type=OUTPUT_TYPE_SOC,
                unit="%",
                values=tuple(soc_values),
            ),
        }

        # Add section-specific outputs
        for section in self._sections:
            section_energy_values = extract_values(section.stored_energy)
            if section.name == BATTERY_SECTION_UNDERCHARGE:
                outputs[BATTERY_UNDERCHARGE_ENERGY_STORED] = OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(section_energy_values)
                )
                outputs[BATTERY_UNDERCHARGE_POWER_DISCHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=tuple(extract_values(section.power_production)),
                    direction="+",
                )
                outputs[BATTERY_UNDERCHARGE_POWER_CHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=tuple(extract_values(section.power_consumption)),
                    direction="-",
                )
                outputs[BATTERY_UNDERCHARGE_CHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=tuple(extract_values(section.charge_cost)),
                    direction="-",
                )
                outputs[BATTERY_UNDERCHARGE_DISCHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=tuple(extract_values(section.discharge_cost)),
                    direction="+",
                )
            elif section.name == BATTERY_SECTION_NORMAL:
                outputs[BATTERY_NORMAL_ENERGY_STORED] = OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(section_energy_values)
                )
                outputs[BATTERY_NORMAL_POWER_DISCHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=tuple(extract_values(section.power_production)),
                    direction="+",
                )
                outputs[BATTERY_NORMAL_POWER_CHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=tuple(extract_values(section.power_consumption)),
                    direction="-",
                )
                outputs[BATTERY_NORMAL_CHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=tuple(extract_values(section.charge_cost)),
                    direction="-",
                )
                outputs[BATTERY_NORMAL_DISCHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=tuple(extract_values(section.discharge_cost)),
                    direction="+",
                )
            elif section.name == BATTERY_SECTION_OVERCHARGE:
                outputs[BATTERY_OVERCHARGE_ENERGY_STORED] = OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=tuple(section_energy_values)
                )
                outputs[BATTERY_OVERCHARGE_POWER_DISCHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=tuple(extract_values(section.power_production)),
                    direction="+",
                )
                outputs[BATTERY_OVERCHARGE_POWER_CHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=tuple(extract_values(section.power_consumption)),
                    direction="-",
                )
                outputs[BATTERY_OVERCHARGE_CHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=tuple(extract_values(section.charge_cost)),
                    direction="-",
                )
                outputs[BATTERY_OVERCHARGE_DISCHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=tuple(extract_values(section.discharge_cost)),
                    direction="+",
                )

        # Shadow prices
        if shadow_prices := self._get_shadow_prices(BATTERY_POWER_BALANCE):
            outputs[BATTERY_POWER_BALANCE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        if shadow_prices := self._get_shadow_prices(BATTERY_MAX_CHARGE_POWER):
            outputs[BATTERY_MAX_CHARGE_POWER] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        if shadow_prices := self._get_shadow_prices(BATTERY_MAX_DISCHARGE_POWER):
            outputs[BATTERY_MAX_DISCHARGE_POWER] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        # Energy balance shadow price from normal section's monotonic_charge constraint
        constraint_name: BatteryConstraintName = f"{BATTERY_SECTION_NORMAL}_monotonic_charge"  # type: ignore[assignment]
        if shadow_prices := self._get_shadow_prices(constraint_name):
            outputs[BATTERY_ENERGY_BALANCE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=tuple(shadow_prices)
            )

        # SOC bounds from section capacity constraints
        constraint_name = f"{BATTERY_SECTION_UNDERCHARGE}_{BATTERY_CAPACITY_LOWER}"  # type: ignore[assignment]
        if shadow_prices := self._get_shadow_prices(constraint_name):
            outputs[BATTERY_SOC_MIN] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=tuple(shadow_prices)
            )

        constraint_name = f"{BATTERY_SECTION_OVERCHARGE}_{BATTERY_CAPACITY_UPPER}"  # type: ignore[assignment]
        if shadow_prices := self._get_shadow_prices(constraint_name):
            outputs[BATTERY_SOC_MAX] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=tuple(shadow_prices)
            )

        # Time slice constraint shadow price
        if shadow_prices := self._get_shadow_prices(BATTERY_TIME_SLICE):
            outputs[BATTERY_TIME_SLICE] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=tuple(shadow_prices)
            )

        # Internal section constraints as shadow prices (for each section that exists)
        for section in self._sections:
            for constraint_suffix in [
                BATTERY_MONOTONIC_CHARGE,
                BATTERY_MONOTONIC_DISCHARGE,
                BATTERY_CAPACITY_UPPER,
                BATTERY_CAPACITY_LOWER,
            ]:
                constraint_name = f"{section.name}_{constraint_suffix}"  # type: ignore[assignment]
                if shadow_prices := self._get_shadow_prices(constraint_name):
                    outputs[constraint_name] = OutputData(
                        type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=tuple(shadow_prices)
                    )

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
