"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

import numpy as np
from pulp import LpAffineExpression, LpVariable, lpSum

from .const import (
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
    OUTPUT_TYPE_SOC,
)
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence, extract_values

# Battery section names
BATTERY_SECTION_UNDERCHARGE: Final[str] = "undercharge"
BATTERY_SECTION_NORMAL: Final[str] = "normal"
BATTERY_SECTION_OVERCHARGE: Final[str] = "overcharge"


def percentage_to_ratio(percentage: Sequence[float] | float | None) -> Sequence[float] | None:
    """Convert percentage (0-100) to ratio (0-1)."""
    if percentage is None:
        return None
    if isinstance(percentage, (int, float)):
        return [percentage / 100.0]
    return [p / 100.0 for p in percentage]


def _is_battery_constraint_name(name: str) -> bool:
    """Check if a constraint name is valid for battery sections."""
    return name.startswith("battery_") and (
        name.endswith("_power_balance")
        or name.endswith("_energy_in_flow")
        or name.endswith("_energy_out_flow")
        or name.endswith("_soc_max")
        or name.endswith("_soc_min")
    )


# Type for battery constraint names (including section-specific ones)
type BatteryConstraintName = Literal[
    "battery_power_balance",
    "battery_normal_energy_in_flow",
    "battery_normal_energy_out_flow",
    "battery_normal_soc_max",
    "battery_normal_soc_min",
    "battery_undercharge_energy_in_flow",
    "battery_undercharge_energy_out_flow",
    "battery_undercharge_soc_max",
    "battery_undercharge_soc_min",
    "battery_overcharge_energy_in_flow",
    "battery_overcharge_energy_out_flow",
    "battery_overcharge_soc_max",
    "battery_overcharge_soc_min",
]

# Type for all battery output names
type BatteryOutputName = (
    Literal[
        "battery_power_charge",
        "battery_power_discharge",
        "battery_energy_stored",
        "battery_state_of_charge",
        "battery_normal_energy_stored",
        "battery_normal_power_charge",
        "battery_normal_power_discharge",
        "battery_normal_charge_price",
        "battery_normal_discharge_price",
        "battery_undercharge_energy_stored",
        "battery_undercharge_power_charge",
        "battery_undercharge_power_discharge",
        "battery_undercharge_charge_price",
        "battery_undercharge_discharge_price",
        "battery_overcharge_energy_stored",
        "battery_overcharge_power_charge",
        "battery_overcharge_power_discharge",
        "battery_overcharge_charge_price",
        "battery_overcharge_discharge_price",
    ]
    | BatteryConstraintName
)

# Battery power constraints
BATTERY_POWER_CONSTRAINTS: Final[frozenset[BatteryConstraintName]] = frozenset(("battery_power_balance",))


class BatterySection:
    """Internal battery section with capacity range and costs.

    Not exposed directly - used internally by Battery for composition.
    """

    def __init__(
        self,
        name: str,
        capacity: Sequence[float],
        charge_cost: Sequence[float],
        discharge_cost: Sequence[float],
        initial_charge: float,
        periods: Sequence[float],
    ) -> None:
        """Initialize a battery section.

        Args:
            name: Name of the section
            capacity: Section capacity in kWh per period
            charge_cost: Cost in $/kWh for charging per period
            discharge_cost: Cost in $/kWh for discharging per period
            initial_charge: Initial charge in kWh
            periods: Sequence of time period durations in hours

        """
        self.name = name
        self.capacity = capacity
        self.charge_cost = [LpAffineExpression(constant=float(c)) for c in charge_cost]
        self.discharge_cost = [LpAffineExpression(constant=float(c)) for c in discharge_cost]
        self.periods = periods
        n_periods = len(periods)

        # Initial charge is set as constant, not variable
        self.energy_in: list[LpAffineExpression | LpVariable] = [
            LpAffineExpression(constant=float(initial_charge)),
            *[LpVariable(f"battery_{name}_energy_in_t{t}", lowBound=0.0) for t in range(1, n_periods + 1)],
        ]
        # Initial discharge is always 0
        self.energy_out: list[LpAffineExpression | LpVariable] = [
            LpAffineExpression(constant=0.0),
            *[LpVariable(f"battery_{name}_energy_out_t{t}", lowBound=0.0) for t in range(1, n_periods + 1)],
        ]

        # Energy flow constraints (cumulative energy can only increase)
        self._constraints: dict[str, Sequence[LpAffineExpression]] = {
            "energy_in_flow": [self.energy_in[t + 1] >= self.energy_in[t] for t in range(n_periods)],
            "energy_out_flow": [self.energy_out[t + 1] >= self.energy_out[t] for t in range(n_periods)],
            # SOC constraints (net energy must stay within capacity)
            "soc_max": [self.energy_in[t + 1] - self.energy_out[t + 1] <= self.capacity[t + 1] for t in range(n_periods)],
            "soc_min": [self.energy_in[t + 1] - self.energy_out[t + 1] >= 0 for t in range(n_periods)],
        }

        # Pre-calculate power and energy expressions to avoid recomputing them
        # Power = Energy / Time, using variable period durations
        self.power_consumption: Sequence[LpAffineExpression] = [
            (self.energy_in[t + 1] - self.energy_in[t]) / self.periods[t] for t in range(n_periods)
        ]
        self.power_production: Sequence[LpAffineExpression] = [
            (self.energy_out[t + 1] - self.energy_out[t]) / self.periods[t] for t in range(n_periods)
        ]
        self.stored_energy: Sequence[LpAffineExpression] = [
            self.energy_in[t] - self.energy_out[t] for t in range(n_periods + 1)
        ]

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    @property
    def constraints(self) -> Mapping[str, Sequence[LpAffineExpression]]:
        """Return constraints with section-specific names."""
        return {
            f"battery_{self.name}_energy_in_flow": self._constraints[BATTERY_ENERGY_IN_FLOW],
            f"battery_{self.name}_energy_out_flow": self._constraints[BATTERY_ENERGY_OUT_FLOW],
            f"battery_{self.name}_soc_max": self._constraints[BATTERY_SOC_MAX],
            f"battery_{self.name}_soc_min": self._constraints[BATTERY_SOC_MIN],
        }

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
        periods: Sequence[float],
        *,
        capacity: Sequence[float] | float,
        initial_charge_percentage: Sequence[float] | float,
        min_charge_percentage: Sequence[float] | float = 10,
        max_charge_percentage: Sequence[float] | float = 90,
        early_charge_incentive: float = 1e-3,
        undercharge_percentage: Sequence[float] | float | None = None,
        overcharge_percentage: Sequence[float] | float | None = None,
        undercharge_cost: Sequence[float] | float | None = None,
        overcharge_cost: Sequence[float] | float | None = None,
    ) -> None:
        """Initialize a battery entity with multi-section modeling.

        Args:
            name: Name of the battery
            periods: Sequence of time period durations in hours (one per optimization interval)
            capacity: Battery capacity in kWh per period
            initial_charge_percentage: Initial charge percentage 0-100
            min_charge_percentage: Preferred minimum charge percentage (inner bound) 0-100
            max_charge_percentage: Preferred maximum charge percentage (inner bound) 0-100
            early_charge_incentive: Positive value ($/kWh) that creates a small incentive
                to prefer earlier charging. Linearly increases from 0 to -incentive across periods.
                Default 0.001 (0.1 cents/kWh) encourages charging earlier when costs are equal.
            undercharge_percentage: Absolute minimum charge percentage (outer bound) 0-100
            overcharge_percentage: Absolute maximum charge percentage (outer bound) 0-100
            undercharge_cost: Cost in $/kWh for discharging in undercharge section
            overcharge_cost: Cost in $/kWh for charging in overcharge section

        Raises:
            ValueError: If percentage parameters violate ordering constraints

        """
        super().__init__(name=name, periods=periods)
        n_periods = self.n_periods

        undercharge_cost = broadcast_to_sequence(undercharge_cost, n_periods)
        overcharge_cost = broadcast_to_sequence(overcharge_cost, n_periods)

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
                    periods=periods,
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
                discharge_cost=(discharge_early_incentive * 2).tolist(),
                initial_charge=section_initial_charge,
                periods=periods,
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
                    discharge_cost=(discharge_early_incentive * 3).tolist(),
                    initial_charge=section_initial_charge,
                    periods=periods,
                )
            )

        # Add section constraints to battery constraints
        for section in self._sections:
            for constraint_name, constraint in section.constraints.items():
                self._constraints[constraint_name] = constraint

        # Pre-calculate power and energy expressions to avoid recomputing them
        # power_consumption: power drawn from network (stored in battery)
        # power_production: power sent to network (released from battery)
        self.power_consumption: Sequence[LpAffineExpression] = [
            lpSum(s.power_consumption[t] for s in self._sections) for t in range(self.n_periods)
        ]
        self.power_production: Sequence[LpAffineExpression] = [
            lpSum(s.power_production[t] for s in self._sections) for t in range(self.n_periods)
        ]
        self.stored_energy: Sequence[LpAffineExpression] = [
            self.inaccessible_energy[t] + lpSum(s.energy_in[t] - s.energy_out[t] for s in self._sections)
            for t in range(self.n_periods + 1)
        ]

    def _validate_parameters(
        self,
        min_charge_ratio: Sequence[float],
        max_charge_ratio: Sequence[float],
        undercharge_ratio: Sequence[float] | None,
        overcharge_ratio: Sequence[float] | None,
        undercharge_cost: Sequence[float] | None,
        overcharge_cost: Sequence[float] | None,
    ) -> None:
        """Validate percentage parameter ordering."""
        # Check min < max for all periods
        for t, (min_r, max_r) in enumerate(zip(min_charge_ratio, max_charge_ratio, strict=False)):
            if min_r >= max_r:
                msg = f"min_charge_ratio ({min_r}) must be less than max_charge_ratio ({max_r}) at period {t}"
                raise ValueError(msg)

        # Check undercharge < min if provided
        if undercharge_ratio is not None:
            if undercharge_cost is None:
                msg = "undercharge_cost must be provided if undercharge_percentage is not None"
                raise ValueError(msg)
            for t, (under_r, min_r) in enumerate(zip(undercharge_ratio, min_charge_ratio, strict=False)):
                if under_r >= min_r:
                    msg = (
                        f"undercharge_ratio ({under_r}) must be less than min_charge_ratio ({min_r}) at period {t}"
                    )
                    raise ValueError(msg)

        # Check max < overcharge if provided
        if overcharge_ratio is not None:
            if overcharge_cost is None:
                msg = "overcharge_cost must be provided if overcharge_percentage is not None"
                raise ValueError(msg)
            for t, (max_r, over_r) in enumerate(zip(max_charge_ratio, overcharge_ratio, strict=False)):
                if max_r >= over_r:
                    msg = (
                        f"overcharge_ratio ({over_r}) must be greater than max_charge_ratio ({max_r}) at period {t}"
                    )
                    raise ValueError(msg)
    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        """

        # Power balance: connection_power equals net battery power
        self._constraints[BATTERY_POWER_BALANCE] = [
            self.connection_power(t) == self.power_consumption[t] - self.power_production[t]
            for t in range(self.n_periods)
        ]

    def cost(self) -> Sequence[LpAffineExpression]:
        """Return the cost expressions of the battery.

        Sum costs from all sections.
        """
        all_costs: list[LpAffineExpression] = []
        for section in self._sections:
            all_costs.extend(section.cost())
        return all_costs

    def outputs(self) -> Mapping[BatteryOutputName, OutputData]:
        """Return battery output specifications."""
        # Get stored energy values
        energy_values = extract_values(self.stored_energy)

        # Calculate SOC percentage
        soc_values = tuple(
            (energy / capacity * 100.0) if capacity > 0 else 0.0
            for energy, capacity in zip(energy_values, self.capacity, strict=False)
        )

        outputs: dict[BatteryOutputName, OutputData] = {
            "battery_power_charge": OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_consumption, direction="-"
            ),
            "battery_power_discharge": OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_production, direction="+"
            ),
            "battery_energy_stored": OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=energy_values),
            "battery_state_of_charge": OutputData(type=OUTPUT_TYPE_SOC, unit="%", values=soc_values),
        }

        # Add section-specific outputs
        for section in self._sections:
            section_energy = extract_values(section.stored_energy)
            section_charge_price = extract_values(section.charge_cost)
            section_discharge_price = extract_values(section.discharge_cost)

            outputs[f"battery_{section.name}_energy_stored"] = OutputData(
                type=OUTPUT_TYPE_ENERGY, unit="kWh", values=section_energy
            )
            outputs[f"battery_{section.name}_power_charge"] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=section.power_consumption, direction="-"
            )
            outputs[f"battery_{section.name}_power_discharge"] = OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=section.power_production, direction="+"
            )
            outputs[f"battery_{section.name}_charge_price"] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=section_charge_price
            )
            outputs[f"battery_{section.name}_discharge_price"] = OutputData(
                type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=section_discharge_price
            )

        # Add power balance constraint shadow prices
        outputs["battery_power_balance"] = OutputData(
            type=OUTPUT_TYPE_SHADOW_PRICE,
            unit="$/kW",
            values=self._constraints["battery_power_balance"],
        )

        # Add section constraint shadow prices
        for section in self._sections:
            for constraint_name in section.constraints:
                outputs[constraint_name] = OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE,
                    unit="$/kWh",
                    values=section.constraints[constraint_name],
                )

        return outputs
