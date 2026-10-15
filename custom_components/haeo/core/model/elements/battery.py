"""Battery entity for electrical system modeling."""

from typing import Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, NetworkElement
from custom_components.haeo.core.model.linear import LinearArray, Rows
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

# Model element type for batteries
ELEMENT_TYPE: Final = "battery"

type BatteryElementTypeName = Literal["battery"]

# Type for battery constraint names (shadow prices exposed as outputs)
type BatteryConstraintName = Literal[
    "element_power_balance",
    "battery_energy_in_flow",
    "battery_energy_out_flow",
    "battery_soc_max",
    "battery_soc_min",
]

# Type for all battery output names (union of base outputs and constraints)
type BatteryOutputName = (
    Literal[
        "battery_power_charge",
        "battery_power_discharge",
        "battery_energy_stored",
    ]
    | BatteryConstraintName
)

# All battery output names (includes constraint shadow prices)
BATTERY_OUTPUT_NAMES: Final[frozenset[BatteryOutputName]] = frozenset(
    (
        # Base outputs
        BATTERY_POWER_CHARGE := "battery_power_charge",
        BATTERY_POWER_DISCHARGE := "battery_power_discharge",
        BATTERY_ENERGY_STORED := "battery_energy_stored",
        # Constraint shadow prices
        BATTERY_POWER_BALANCE := ELEMENT_POWER_BALANCE,
        BATTERY_ENERGY_IN_FLOW := "battery_energy_in_flow",
        BATTERY_ENERGY_OUT_FLOW := "battery_energy_out_flow",
        BATTERY_SOC_MAX := "battery_soc_max",
        BATTERY_SOC_MIN := "battery_soc_min",
    )
)

# Battery power constraints (subset of outputs that relate to power balance)
BATTERY_POWER_CONSTRAINTS: Final[frozenset[BatteryConstraintName]] = frozenset((BATTERY_POWER_BALANCE,))


class BatteryElementConfig(TypedDict):
    """Configuration for Battery model elements."""

    element_type: BatteryElementTypeName
    name: str
    capacity: NDArray[np.float64] | float
    initial_charge: float
    min_charge: NotRequired[NDArray[np.float64] | float]
    max_charge: NotRequired[NDArray[np.float64] | float]
    charge_limit_cost: NotRequired[NDArray[np.float64] | float]
    salvage_value: NotRequired[float]
    outbound_tags: NotRequired[set[int] | None]
    inbound_tags: NotRequired[set[int] | None]


class Battery(NetworkElement[BatteryOutputName]):
    """Battery entity for electrical system modeling.

    Represents a single battery section with cumulative energy tracking.
    Stored energy runs from empty to its capacity. The min and max charge are kept
    with priced slack instead, so the plan stays feasible when the battery starts
    outside them. Uses TrackedParam for parameters that can change between optimizations.
    """

    # Parameters
    capacity: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_charge: TrackedParam[float] = TrackedParam()
    min_charge: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    max_charge: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    charge_limit_cost: TrackedParam[NDArray[np.float64]] = TrackedParam()
    salvage_value: TrackedParam[float] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        capacity: NDArray[np.float64] | float,
        initial_charge: float,
        min_charge: NDArray[np.float64] | float | None = None,
        max_charge: NDArray[np.float64] | float | None = None,
        charge_limit_cost: NDArray[np.float64] | float | None = None,
        salvage_value: float = 0.0,
        outbound_tags: set[int] | None = None,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a battery entity."""
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=BATTERY_OUTPUT_NAMES,
            outbound_tags=outbound_tags,
            inbound_tags=inbound_tags,
        )
        n_periods = self.n_periods

        # Set tracked parameters (broadcasts capacity to n_periods + 1)
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)
        self.initial_charge = initial_charge
        self.min_charge = broadcast_to_sequence(min_charge, n_periods + 1)
        self.max_charge = broadcast_to_sequence(max_charge, n_periods + 1)
        if charge_limit_cost is None:
            if min_charge is not None or max_charge is not None:
                msg = f"Battery '{name}' needs a charge limit cost to hold its min or max charge"
                raise ValueError(msg)
            charge_limit_cost = 0.0
        self.charge_limit_cost = broadcast_to_sequence(charge_limit_cost, n_periods)
        self.salvage_value = salvage_value

        # Create all energy variables (including initial state at t=0)
        self.energy_in = solver.add_variables(n_periods + 1, name=f"{name}.energy_in")
        self.energy_out = solver.add_variables(n_periods + 1, name=f"{name}.energy_out")

        # Stored energy is computed from cumulative values (not period-dependent)
        self.stored_energy = self.energy_in - self.energy_out

        # Energy below the min charge and above the max charge at each boundary after the first
        self._below_min = solver.add_variables(n_periods, name=f"{name}.below_min")
        self._above_max = solver.add_variables(n_periods, name=f"{name}.above_max")

    @property
    def charge_floor(self) -> NDArray[np.float64]:
        """Stored energy the battery is held above at each boundary: its min charge, or empty when unset."""
        return np.zeros(self.n_periods + 1) if self.min_charge is None else self.min_charge

    @property
    def charge_ceiling(self) -> NDArray[np.float64]:
        """Stored energy the battery is held below at each boundary: its max charge, or full when unset."""
        return self.capacity if self.max_charge is None else self.max_charge

    @property
    def power_consumption(self) -> LinearArray:
        """Power being consumed to charge the battery.

        Computed on-demand so that accessing self.periods triggers dependency tracking
        when called from within @constraint or @cost decorated methods.
        """
        return (self.energy_in[1:] - self.energy_in[:-1]) * (1.0 / self.periods)

    @property
    def power_production(self) -> LinearArray:
        """Power being produced by discharging the battery.

        Computed on-demand so that accessing self.periods triggers dependency tracking
        when called from within @constraint or @cost decorated methods.
        """
        return (self.energy_out[1:] - self.energy_out[:-1]) * (1.0 / self.periods)

    @constraint
    def battery_initial_charge(self) -> Rows:
        """Constraint: energy_in[0] == initial_charge."""
        return self.energy_in[0] == self.initial_charge

    @constraint
    def battery_initial_discharge(self) -> Rows:
        """Constraint: energy_out[0] == 0."""
        return self.energy_out[0] == 0.0

    @constraint(output=True, unit="$/kWh")
    def battery_energy_in_flow(self) -> Rows:
        """Constraint: cumulative energy in can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return self.energy_in[:-1] <= self.energy_in[1:]

    @constraint(output=True, unit="$/kWh")
    def battery_energy_out_flow(self) -> Rows:
        """Constraint: cumulative energy out can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return self.energy_out[:-1] <= self.energy_out[1:]

    @constraint
    def battery_full(self) -> Rows:
        """Constraint: energy above the max charge fits in the capacity, so the battery never overfills.

        With no max charge, there is no room above it and the max charge row holds at the capacity.
        """
        return self._above_max - (self.capacity[1:] - self.charge_ceiling[1:]) <= 0.0

    @constraint
    def battery_empty(self) -> Rows:
        """Constraint: energy below the min charge is at most the min charge, so the battery never goes negative.

        With no min charge, there is no room below it and the min charge row holds at empty.
        """
        return self._below_min - self.charge_floor[1:] <= 0.0

    @constraint(output=True, unit="$/kWh")
    def battery_soc_max(self) -> Rows:
        """Constraint: stored energy stays at or below the max charge, or pays for the excess.

        Output: shadow price indicating the marginal value of a higher max charge.
        """
        return self.stored_energy[1:] - self._above_max <= self.charge_ceiling[1:]

    @constraint(output=True, unit="$/kWh")
    def battery_soc_min(self) -> Rows:
        """Constraint: stored energy stays at or above the min charge, or pays for the shortfall.

        Output: shadow price indicating the marginal cost of the min charge.
        """
        return self.stored_energy[1:] + self._below_min >= self.charge_floor[1:]

    def element_power_produced(self) -> LinearArray:
        """Return power produced by discharging the battery."""
        return self.power_production

    def element_power_consumed(self) -> LinearArray:
        """Return power consumed by charging the battery."""
        return self.power_consumption

    @cost
    def battery_charge_limit_cost(self) -> LinearArray:
        """Cost: holding cost for energy outside the min and max charge, per hour.

        Set high, it makes the limits hard in practice while a battery reported
        outside them still gives a feasible plan that returns it inside. It is
        priced per hour so a period costs the same whether it is planned as one
        long period or later as several short ones.
        """
        return ((self._below_min + self._above_max) * (self.charge_limit_cost * self.periods)).total()

    @cost
    def battery_salvage_value(self) -> LinearArray:
        """Cost: salvage value of stored energy at the end of the horizon."""
        return -self.salvage_value * self.stored_energy[-1]

    # Output methods

    @output
    def battery_power_charge(self) -> OutputData:
        """Output: power being consumed to charge the battery."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
        )

    @output
    def battery_power_discharge(self) -> OutputData:
        """Output: power being produced by discharging the battery."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_production), direction="+"
        )

    @output
    def battery_energy_stored(self) -> OutputData:
        """Output: energy currently stored in the battery."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self.extract_values(self.stored_energy))
