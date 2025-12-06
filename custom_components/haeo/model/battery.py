"""Battery entity for electrical system modeling."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal, TypeGuard

import numpy as np
from pulp import LpAffineExpression, LpConstraint, LpVariable
from pulp.pulp import lpSum

from .const import OUTPUT_TYPE_ENERGY, OUTPUT_TYPE_POWER, OUTPUT_TYPE_PRICE, OUTPUT_TYPE_SHADOW_PRICE, OUTPUT_TYPE_SOC
from .element import Element
from .output_data import OutputData
from .util import broadcast_to_sequence, extract_values, percentage_to_ratio

# Battery section names
BATTERY_SECTION_UNDERCHARGE: Final = "undercharge"
BATTERY_SECTION_NORMAL: Final = "normal"
BATTERY_SECTION_OVERCHARGE: Final = "overcharge"

# Battery constraint names (also used as shadow price output names)
BATTERY_POWER_BALANCE: Final = "battery_power_balance"

# Internal section constraint name patterns (used to build shadow price outputs)
BATTERY_ENERGY_IN_FLOW: Final = "energy_in_flow"
BATTERY_ENERGY_OUT_FLOW: Final = "energy_out_flow"
BATTERY_SOC_MAX: Final = "soc_max"
BATTERY_SOC_MIN: Final = "soc_min"

# Battery output names
BATTERY_POWER_CHARGE: Final = "battery_power_charge"
BATTERY_POWER_DISCHARGE: Final = "battery_power_discharge"
BATTERY_ENERGY_STORED: Final = "battery_energy_stored"
BATTERY_STATE_OF_CHARGE: Final = "battery_state_of_charge"

# Section-specific output names
BATTERY_UNDERCHARGE_ENERGY_STORED: Final = "battery_undercharge_energy_stored"
BATTERY_UNDERCHARGE_POWER_CHARGE: Final = "battery_undercharge_power_charge"
BATTERY_UNDERCHARGE_POWER_DISCHARGE: Final = "battery_undercharge_power_discharge"
BATTERY_UNDERCHARGE_CHARGE_PRICE: Final = "battery_undercharge_charge_price"
BATTERY_UNDERCHARGE_DISCHARGE_PRICE: Final = "battery_undercharge_discharge_price"
BATTERY_UNDERCHARGE_ENERGY_IN_FLOW: Final = "battery_undercharge_energy_in_flow"
BATTERY_UNDERCHARGE_ENERGY_OUT_FLOW: Final = "battery_undercharge_energy_out_flow"
BATTERY_UNDERCHARGE_SOC_MAX: Final = "battery_undercharge_soc_max"
BATTERY_UNDERCHARGE_SOC_MIN: Final = "battery_undercharge_soc_min"

BATTERY_NORMAL_ENERGY_STORED: Final = "battery_normal_energy_stored"
BATTERY_NORMAL_POWER_CHARGE: Final = "battery_normal_power_charge"
BATTERY_NORMAL_POWER_DISCHARGE: Final = "battery_normal_power_discharge"
BATTERY_NORMAL_CHARGE_PRICE: Final = "battery_normal_charge_price"
BATTERY_NORMAL_DISCHARGE_PRICE: Final = "battery_normal_discharge_price"
BATTERY_NORMAL_ENERGY_IN_FLOW: Final = "battery_normal_energy_in_flow"
BATTERY_NORMAL_ENERGY_OUT_FLOW: Final = "battery_normal_energy_out_flow"
BATTERY_NORMAL_SOC_MAX: Final = "battery_normal_soc_max"
BATTERY_NORMAL_SOC_MIN: Final = "battery_normal_soc_min"

BATTERY_OVERCHARGE_ENERGY_STORED: Final = "battery_overcharge_energy_stored"
BATTERY_OVERCHARGE_POWER_CHARGE: Final = "battery_overcharge_power_charge"
BATTERY_OVERCHARGE_POWER_DISCHARGE: Final = "battery_overcharge_power_discharge"
BATTERY_OVERCHARGE_CHARGE_PRICE: Final = "battery_overcharge_charge_price"
BATTERY_OVERCHARGE_DISCHARGE_PRICE: Final = "battery_overcharge_discharge_price"
BATTERY_OVERCHARGE_ENERGY_IN_FLOW: Final = "battery_overcharge_energy_in_flow"
BATTERY_OVERCHARGE_ENERGY_OUT_FLOW: Final = "battery_overcharge_energy_out_flow"
BATTERY_OVERCHARGE_SOC_MAX: Final = "battery_overcharge_soc_max"
BATTERY_OVERCHARGE_SOC_MIN: Final = "battery_overcharge_soc_min"

# Type for battery constraint names (includes all internal and external constraints)
type BatteryConstraintName = Literal[
    "battery_power_balance",
    "battery_undercharge_energy_in_flow",
    "battery_undercharge_energy_out_flow",
    "battery_undercharge_soc_max",
    "battery_undercharge_soc_min",
    "battery_normal_energy_in_flow",
    "battery_normal_energy_out_flow",
    "battery_normal_soc_max",
    "battery_normal_soc_min",
    "battery_overcharge_energy_in_flow",
    "battery_overcharge_energy_out_flow",
    "battery_overcharge_soc_max",
    "battery_overcharge_soc_min",
]

# Type for all battery output names (union of base outputs and constraints)
type BatteryOutputName = (
    Literal[
        "battery_power_charge",
        "battery_power_discharge",
        "battery_energy_stored",
        "battery_state_of_charge",
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
        BATTERY_UNDERCHARGE_ENERGY_IN_FLOW,
        BATTERY_UNDERCHARGE_ENERGY_OUT_FLOW,
        BATTERY_UNDERCHARGE_SOC_MAX,
        BATTERY_UNDERCHARGE_SOC_MIN,
        BATTERY_NORMAL_ENERGY_IN_FLOW,
        BATTERY_NORMAL_ENERGY_OUT_FLOW,
        BATTERY_NORMAL_SOC_MAX,
        BATTERY_NORMAL_SOC_MIN,
        BATTERY_OVERCHARGE_ENERGY_IN_FLOW,
        BATTERY_OVERCHARGE_ENERGY_OUT_FLOW,
        BATTERY_OVERCHARGE_SOC_MAX,
        BATTERY_OVERCHARGE_SOC_MIN,
    )
)

BATTERY_CONSTRAINT_NAMES: Final[frozenset[BatteryConstraintName]] = frozenset(
    (
        BATTERY_POWER_BALANCE,
        BATTERY_UNDERCHARGE_ENERGY_IN_FLOW,
        BATTERY_UNDERCHARGE_ENERGY_OUT_FLOW,
        BATTERY_UNDERCHARGE_SOC_MAX,
        BATTERY_UNDERCHARGE_SOC_MIN,
        BATTERY_NORMAL_ENERGY_IN_FLOW,
        BATTERY_NORMAL_ENERGY_OUT_FLOW,
        BATTERY_NORMAL_SOC_MAX,
        BATTERY_NORMAL_SOC_MIN,
        BATTERY_OVERCHARGE_ENERGY_IN_FLOW,
        BATTERY_OVERCHARGE_ENERGY_OUT_FLOW,
        BATTERY_OVERCHARGE_SOC_MAX,
        BATTERY_OVERCHARGE_SOC_MIN,
    )
)

BATTERY_POWER_CONSTRAINTS: Final[frozenset[BatteryConstraintName]] = frozenset((BATTERY_POWER_BALANCE,))


def _is_battery_constraint_name(name: str) -> TypeGuard[BatteryConstraintName]:
    """Check if a string is a valid battery constraint name."""
    return name in BATTERY_CONSTRAINT_NAMES


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

        self.constraints: dict[BatteryConstraintName, list[LpConstraint]] = {
            self._section_constraint(BATTERY_ENERGY_IN_FLOW): [
                self.energy_in[t + 1] >= self.energy_in[t] for t in range(n_periods)
            ],
            self._section_constraint(BATTERY_ENERGY_OUT_FLOW): [
                self.energy_out[t + 1] >= self.energy_out[t] for t in range(n_periods)
            ],
            self._section_constraint(BATTERY_SOC_MAX): [
                self.energy_in[t + 1] - self.energy_out[t + 1] <= capacity[t + 1] for t in range(n_periods)
            ],
            self._section_constraint(BATTERY_SOC_MIN): [
                self.energy_in[t + 1] - self.energy_out[t + 1] >= 0 for t in range(n_periods)
            ],
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

    def _section_constraint(self, inner_name: str) -> BatteryConstraintName:
        name = f"battery_{self.name}_{inner_name}"
        if not _is_battery_constraint_name(name):
            msg = f"Unknown battery constraint name '{name}'"
            raise ValueError(msg)
        return name

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
        early_charge_incentive: float = 1e-3,
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
        super().__init__(name=name, period=period, n_periods=n_periods)

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
                discharge_cost=(discharge_early_incentive * 2).tolist(),
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
                    discharge_cost=(discharge_early_incentive * 3).tolist(),
                    initial_charge=section_initial_charge,
                    period=period,
                    n_periods=n_periods,
                )
            )

        # Add section constraints to battery constraints
        for section in self._sections:
            for constraint_name, constraint in section.constraints.items():
                self._constraints[constraint_name] = constraint

        # Pre-calculate power and energy expressions to avoid recomputing them
        # power_consumption: power drawn from network (stored in battery)
        # power_production: power sent to network (released from battery)
        # Note: Efficiency and power limits are now handled by Connection objects
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

    def build_constraints(self) -> None:
        """Build network-dependent constraints for the battery.

        This includes power balance constraints using connection_power().
        Note: Efficiency losses and power limits are now handled by Connection objects.
        """

        # Power balance: connection_power equals net battery power
        # Efficiency losses and power limits are handled by the Connection to the battery
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
        # Get total energy stored values (needed for SOC calculation)
        total_energy_values = extract_values(self.stored_energy)

        # Convert to SOC percentage
        capacity_array = np.array(self.capacity)
        soc_values = (np.array(total_energy_values) / capacity_array * 100.0).tolist()

        outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_POWER_CHARGE: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_consumption, direction="-"
            ),
            BATTERY_POWER_DISCHARGE: OutputData(
                type=OUTPUT_TYPE_POWER, unit="kW", values=self.power_production, direction="+"
            ),
            BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=total_energy_values),
            BATTERY_STATE_OF_CHARGE: OutputData(
                type=OUTPUT_TYPE_SOC,
                unit="%",
                values=soc_values,
            ),
        }

        # Add section-specific outputs
        for section in self._sections:
            if section.name == BATTERY_SECTION_UNDERCHARGE:
                outputs[BATTERY_UNDERCHARGE_ENERGY_STORED] = OutputData(
                    type=OUTPUT_TYPE_ENERGY,
                    unit="kWh",
                    values=section.stored_energy,
                    advanced=True,
                )
                outputs[BATTERY_UNDERCHARGE_POWER_DISCHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=section.power_production,
                    direction="+",
                    advanced=True,
                )
                outputs[BATTERY_UNDERCHARGE_POWER_CHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=section.power_consumption,
                    direction="-",
                    advanced=True,
                )
                outputs[BATTERY_UNDERCHARGE_CHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=section.charge_cost,
                    direction="-",
                    advanced=True,
                )
                outputs[BATTERY_UNDERCHARGE_DISCHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=section.discharge_cost,
                    direction="+",
                    advanced=True,
                )
            elif section.name == BATTERY_SECTION_NORMAL:
                outputs[BATTERY_NORMAL_ENERGY_STORED] = OutputData(
                    type=OUTPUT_TYPE_ENERGY,
                    unit="kWh",
                    values=section.stored_energy,
                    advanced=True,
                )
                outputs[BATTERY_NORMAL_POWER_DISCHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=section.power_production,
                    direction="+",
                    advanced=True,
                )
                outputs[BATTERY_NORMAL_POWER_CHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=section.power_consumption,
                    direction="-",
                    advanced=True,
                )
                outputs[BATTERY_NORMAL_CHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=section.charge_cost,
                    direction="-",
                    advanced=True,
                )
                outputs[BATTERY_NORMAL_DISCHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=section.discharge_cost,
                    direction="+",
                    advanced=True,
                )
            elif section.name == BATTERY_SECTION_OVERCHARGE:
                outputs[BATTERY_OVERCHARGE_ENERGY_STORED] = OutputData(
                    type=OUTPUT_TYPE_ENERGY,
                    unit="kWh",
                    values=section.stored_energy,
                    advanced=True,
                )
                outputs[BATTERY_OVERCHARGE_POWER_DISCHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=section.power_production,
                    direction="+",
                    advanced=True,
                )
                outputs[BATTERY_OVERCHARGE_POWER_CHARGE] = OutputData(
                    type=OUTPUT_TYPE_POWER,
                    unit="kW",
                    values=section.power_consumption,
                    direction="-",
                    advanced=True,
                )
                outputs[BATTERY_OVERCHARGE_CHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=section.charge_cost,
                    direction="-",
                    advanced=True,
                )
                outputs[BATTERY_OVERCHARGE_DISCHARGE_PRICE] = OutputData(
                    type=OUTPUT_TYPE_PRICE,
                    unit="$/kWh",
                    values=section.discharge_cost,
                    direction="+",
                    advanced=True,
                )

        for constraint_name in self._constraints:
            unit = "$/kW" if constraint_name in BATTERY_POWER_CONSTRAINTS else "$/kWh"
            outputs[constraint_name] = OutputData(
                type=OUTPUT_TYPE_SHADOW_PRICE,
                unit=unit,
                values=self._constraints[constraint_name],
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
