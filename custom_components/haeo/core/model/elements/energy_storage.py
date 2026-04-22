"""Energy storage element for electrical system modeling."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, NetworkElement
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.core.model.util import broadcast_to_sequence

# Model element type for energy storage
ELEMENT_TYPE: Final = "energy_storage"
type EnergyStorageElementTypeName = Literal["energy_storage"]

# Type for constraint names (shadow prices exposed as outputs)
type EnergyStorageConstraintName = Literal[
    "element_power_balance",
    "energy_storage_energy_in_flow",
    "energy_storage_energy_out_flow",
    "energy_storage_soc_max",
    "energy_storage_soc_min",
]

# Type for all output names (union of base outputs and constraints)
type EnergyStorageOutputName = (
    Literal[
        "energy_storage_power_charge",
        "energy_storage_power_discharge",
        "energy_storage_energy_stored",
    ]
    | EnergyStorageConstraintName
)

# All output names (includes constraint shadow prices)
ENERGY_STORAGE_OUTPUT_NAMES: Final[frozenset[EnergyStorageOutputName]] = frozenset(
    (
        # Base outputs
        ENERGY_STORAGE_POWER_CHARGE := "energy_storage_power_charge",
        ENERGY_STORAGE_POWER_DISCHARGE := "energy_storage_power_discharge",
        ENERGY_STORAGE_ENERGY_STORED := "energy_storage_energy_stored",
        # Constraint shadow prices
        ENERGY_STORAGE_POWER_BALANCE := ELEMENT_POWER_BALANCE,
        ENERGY_STORAGE_ENERGY_IN_FLOW := "energy_storage_energy_in_flow",
        ENERGY_STORAGE_ENERGY_OUT_FLOW := "energy_storage_energy_out_flow",
        ENERGY_STORAGE_SOC_MAX := "energy_storage_soc_max",
        ENERGY_STORAGE_SOC_MIN := "energy_storage_soc_min",
    )
)

# Power constraints (subset of outputs that relate to power balance)
ENERGY_STORAGE_POWER_CONSTRAINTS: Final[frozenset[EnergyStorageConstraintName]] = frozenset(
    (ENERGY_STORAGE_POWER_BALANCE,)
)


class InventoryCostSpec(TypedDict):
    """Specification for a single inventory level cost."""

    direction: Literal["above", "below"]
    threshold: NDArray[np.floating[Any]] | float
    price: NDArray[np.floating[Any]] | float


class EnergyStorageElementConfig(TypedDict):
    """Configuration for EnergyStorage model elements."""

    element_type: EnergyStorageElementTypeName
    name: str
    capacity: NDArray[np.floating[Any]] | float
    initial_charge: float
    salvage_value: NotRequired[float]
    inventory_costs: NotRequired[list[InventoryCostSpec]]
    outbound_tags: NotRequired[set[int] | None]
    inbound_tags: NotRequired[set[int] | None]


class EnergyStorage(NetworkElement[EnergyStorageOutputName]):
    """Energy storage element for electrical system modeling.

    Represents energy storage with cumulative energy tracking and
    optional inventory level costs that penalize stored energy being
    above or below configurable thresholds.
    """

    # Parameters
    capacity: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_charge: TrackedParam[float] = TrackedParam()
    salvage_value: TrackedParam[float] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        capacity: NDArray[np.floating[Any]] | float,
        initial_charge: float,
        salvage_value: float = 0.0,
        inventory_costs: list[InventoryCostSpec] | None = None,
        outbound_tags: set[int] | None = None,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize an energy storage element."""
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=ENERGY_STORAGE_OUTPUT_NAMES,
            outbound_tags=outbound_tags,
            inbound_tags=inbound_tags,
        )
        n_periods = self.n_periods

        # Set tracked parameters (broadcasts capacity to n_periods + 1)
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)
        self.initial_charge = initial_charge
        self.salvage_value = salvage_value

        # Create all energy variables (including initial state at t=0)
        self.energy_in = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_energy_in_", out_array=True)
        self.energy_out = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_energy_out_", out_array=True)

        # Stored energy is computed from cumulative values (not period-dependent)
        self.stored_energy = self.energy_in - self.energy_out

        # Create inventory cost slack variables
        self._inventory_costs: list[
            tuple[InventoryCostSpec, NDArray[np.floating[Any]], NDArray[np.floating[Any]], HighspyArray]
        ] = []
        for i, ic in enumerate(inventory_costs or []):
            threshold = broadcast_to_sequence(ic["threshold"], n_periods)
            price = broadcast_to_sequence(ic["price"], n_periods)
            slack = solver.addVariables(
                n_periods,
                lb=0.0,
                name_prefix=f"{name}_inventory_{i}_{ic['direction']}_",
                out_array=True,
            )
            self._inventory_costs.append((ic, threshold, price, slack))

    @property
    def power_consumption(self) -> HighspyArray:
        """Power being consumed to charge the storage.

        Computed on-demand so that accessing self.periods triggers dependency tracking
        when called from within @constraint or @cost decorated methods.
        """
        return (self.energy_in[1:] - self.energy_in[:-1]) * (1.0 / self.periods)

    @property
    def power_production(self) -> HighspyArray:
        """Power being produced by discharging the storage.

        Computed on-demand so that accessing self.periods triggers dependency tracking
        when called from within @constraint or @cost decorated methods.
        """
        return (self.energy_out[1:] - self.energy_out[:-1]) * (1.0 / self.periods)

    @constraint
    def energy_storage_initial_charge(self) -> highs_linear_expression:
        """Constraint: energy_in[0] == initial_charge."""
        return self.energy_in[0] == self.initial_charge

    @constraint
    def energy_storage_initial_discharge(self) -> highs_linear_expression:
        """Constraint: energy_out[0] == 0."""
        return self.energy_out[0] == 0.0

    @constraint(output=True, unit="$/kWh")
    def energy_storage_energy_in_flow(self) -> list[highs_linear_expression]:
        """Constraint: cumulative energy in can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return list(self.energy_in[1:] >= self.energy_in[:-1])

    @constraint(output=True, unit="$/kWh")
    def energy_storage_energy_out_flow(self) -> list[highs_linear_expression]:
        """Constraint: cumulative energy out can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return list(self.energy_out[1:] >= self.energy_out[:-1])

    @constraint(output=True, unit="$/kWh")
    def energy_storage_soc_max(self) -> list[highs_linear_expression]:
        """Constraint: stored energy cannot exceed capacity.

        Output: shadow price indicating the marginal value of additional capacity.
        """
        return list(self.stored_energy[1:] <= self.capacity[1:])

    @constraint(output=True, unit="$/kWh")
    def energy_storage_soc_min(self) -> list[highs_linear_expression]:
        """Constraint: stored energy cannot be negative.

        Output: shadow price indicating the marginal cost of minimum SOC constraint.
        """
        return list(self.stored_energy[1:] >= 0)

    @constraint
    def inventory_cost_bounds(self) -> list[highs_linear_expression] | None:
        """Constraints: slack variables bound to threshold violations.

        For "below" direction: slack >= threshold - stored_energy
        For "above" direction: slack >= stored_energy - threshold
        """
        if not self._inventory_costs:
            return None
        stored_energy = np.asarray(self.stored_energy, dtype=object)
        constraints: list[highs_linear_expression] = []
        for spec, threshold, _price, slack in self._inventory_costs:
            if spec["direction"] == "below":
                constraints.extend(list(slack >= threshold - stored_energy[1:]))
            else:
                constraints.extend(list(slack >= stored_energy[1:] - threshold))
        return constraints

    def element_power_produced(self) -> HighspyArray:
        """Return power produced by discharging the storage."""
        return self.power_production

    def element_power_consumed(self) -> HighspyArray:
        """Return power consumed by charging the storage."""
        return self.power_consumption

    @cost
    def energy_storage_salvage_value(self) -> highs_linear_expression:
        """Cost: salvage value of stored energy at the end of the horizon."""
        return -self.salvage_value * self.stored_energy[-1]

    @cost
    def inventory_level_cost(self) -> highs_linear_expression | None:
        """Cost: penalty for stored energy above/below inventory thresholds.

        Each inventory cost rule adds a per-period penalty proportional to the
        amount by which stored energy exceeds or falls short of the threshold.
        Costs stack across rules.
        """
        if not self._inventory_costs:
            return None
        cost_terms = []
        for _spec, _threshold, price, slack in self._inventory_costs:
            cost_terms.append(Highs.qsum(slack * price))
        if len(cost_terms) == 1:
            return cost_terms[0]
        return Highs.qsum(cost_terms)

    # Output methods

    @output
    def energy_storage_power_charge(self) -> OutputData:
        """Output: power being consumed to charge the storage."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
        )

    @output
    def energy_storage_power_discharge(self) -> OutputData:
        """Output: power being produced by discharging the storage."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_production), direction="+"
        )

    @output
    def energy_storage_energy_stored(self) -> OutputData:
        """Output: energy currently stored."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self.extract_values(self.stored_energy))


# Backwards-compatible aliases used by the battery adapter layer
BATTERY_POWER_CHARGE = ENERGY_STORAGE_POWER_CHARGE
BATTERY_POWER_DISCHARGE = ENERGY_STORAGE_POWER_DISCHARGE
BATTERY_ENERGY_STORED = ENERGY_STORAGE_ENERGY_STORED
BATTERY_POWER_BALANCE = ENERGY_STORAGE_POWER_BALANCE
BATTERY_ENERGY_IN_FLOW = ENERGY_STORAGE_ENERGY_IN_FLOW
BATTERY_ENERGY_OUT_FLOW = ENERGY_STORAGE_ENERGY_OUT_FLOW
BATTERY_SOC_MAX = ENERGY_STORAGE_SOC_MAX
BATTERY_SOC_MIN = ENERGY_STORAGE_SOC_MIN
