"""Deferrable load entity for electrical system modeling.

A deferrable load absorbs a required amount of energy within scheduled
windows (e.g. calendar events). Rather than enforcing the requirement as a
hard constraint, a shortfall is priced at the boundary where the missed
requirement falls due, and absorption beyond the total requirement is
priced once at the end of the horizon. This keeps the optimization feasible
when the requirement physically cannot be met while still making the
optimizer work hard to meet it.
"""

from typing import Any, Final, Literal, NotRequired, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, NetworkElement
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.core.model.util import broadcast_to_sequence, require_non_negative

# Model element type for deferrable loads
ELEMENT_TYPE: Final = "deferrable_load"
type DeferrableLoadElementTypeName = Literal["deferrable_load"]

# Type for deferrable load constraint names (shadow prices exposed as outputs)
type DeferrableLoadConstraintName = Literal[
    "element_power_balance",
    "deferrable_load_energy_flow",
    "deferrable_load_capacity",
    "deferrable_load_requirement",
]

# Type for all deferrable load output names (union of base outputs and constraints)
type DeferrableLoadOutputName = (
    Literal[
        "deferrable_load_power",
        "deferrable_load_energy_absorbed",
        "deferrable_load_energy_deficit",
    ]
    | DeferrableLoadConstraintName
)

# All deferrable load output names (includes constraint shadow prices)
DEFERRABLE_LOAD_OUTPUT_NAMES: Final[frozenset[DeferrableLoadOutputName]] = frozenset(
    (
        # Base outputs
        DEFERRABLE_LOAD_POWER := "deferrable_load_power",
        DEFERRABLE_LOAD_ENERGY_ABSORBED := "deferrable_load_energy_absorbed",
        DEFERRABLE_LOAD_ENERGY_DEFICIT := "deferrable_load_energy_deficit",
        # Constraint shadow prices
        DEFERRABLE_LOAD_POWER_BALANCE := ELEMENT_POWER_BALANCE,
        DEFERRABLE_LOAD_ENERGY_FLOW := "deferrable_load_energy_flow",
        DEFERRABLE_LOAD_CAPACITY := "deferrable_load_capacity",
        DEFERRABLE_LOAD_REQUIREMENT := "deferrable_load_requirement",
    )
)


class DeferrableLoadElementConfig(TypedDict):
    """Configuration for DeferrableLoad model elements."""

    element_type: DeferrableLoadElementTypeName
    name: str
    capacity: NDArray[np.floating[Any]] | float
    required: NDArray[np.floating[Any]] | float
    initial_energy: NotRequired[float]
    deficit_price: NDArray[np.floating[Any]] | float
    overage_price: NotRequired[float]
    outbound_tags: NotRequired[set[int] | None]
    inbound_tags: NotRequired[set[int] | None]


class DeferrableLoad(NetworkElement[DeferrableLoadOutputName]):
    """Deferrable load entity for electrical system modeling.

    Tracks cumulative absorbed energy against two boundary-aligned profiles:

    - ``capacity``: the maximum cumulative energy absorbable by each boundary
      (opens as scheduled windows begin).
    - ``required``: the cumulative energy that should have been absorbed by
      each boundary (due as scheduled windows end).

    The deficit variable is non-decreasing, so a shortfall against the
    requirement at any boundary stays locked in even if absorption later
    catches up. Each boundary's deficit increment is limited to the
    requirement newly falling due there and priced at that boundary's
    ``deficit_price`` (a scalar applies uniformly), so a shortfall is never
    booked at a boundary before it is due. Absorption beyond the final
    requirement is priced at ``overage_price``.

    Both prices must be non-negative: a negative price would reward booking
    a shortfall or overshoot that never happens. Both slacks are also
    bounded above by what could physically fall short or overshoot, so they
    stay bounded even when unpriced.
    """

    # Parameters
    capacity: TrackedParam[NDArray[np.float64]] = TrackedParam()
    required: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_energy: TrackedParam[float] = TrackedParam()
    deficit_price: TrackedParam[NDArray[np.float64]] = TrackedParam()
    overage_price: TrackedParam[float] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        *,
        solver: Highs,
        capacity: NDArray[np.floating[Any]] | float,
        required: NDArray[np.floating[Any]] | float,
        deficit_price: NDArray[np.floating[Any]] | float,
        initial_energy: float = 0.0,
        overage_price: float = 0.0,
        outbound_tags: set[int] | None = None,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a deferrable load entity."""
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=DEFERRABLE_LOAD_OUTPUT_NAMES,
            outbound_tags=outbound_tags,
            inbound_tags=inbound_tags,
        )
        n_periods = self.n_periods

        # Set tracked parameters (broadcasts profiles to n_periods + 1)
        self.capacity = broadcast_to_sequence(capacity, n_periods + 1)
        self.required = broadcast_to_sequence(required, n_periods + 1)
        self.initial_energy = initial_energy
        self.deficit_price = broadcast_to_sequence(deficit_price, n_periods + 1)
        self.overage_price = overage_price

        # Cumulative absorbed energy (including initial state at t=0)
        self.energy = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_energy_", out_array=True)
        # Locked-in shortfall against the requirement at each boundary
        self.deficit = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_deficit_", out_array=True)
        # Absorption beyond the final requirement
        self.overage = solver.addVariables(1, lb=0.0, name_prefix=f"{name}_overage_", out_array=True)

    @property
    def power_consumption(self) -> HighspyArray:
        """Power being consumed to absorb energy.

        Computed on-demand so that accessing self.periods triggers dependency
        tracking when called from within @constraint or @cost decorated methods.
        """
        return (self.energy[1:] - self.energy[:-1]) * (1.0 / self.periods)

    @constraint
    def deferrable_load_initial_energy(self) -> highs_linear_expression:
        """Constraint: energy[0] == initial_energy."""
        return self.energy[0] == self.initial_energy

    @constraint
    def deferrable_load_initial_deficit(self) -> highs_linear_expression:
        """Constraint: deficit[0] == 0."""
        return self.deficit[0] == 0.0

    @constraint(output=True, unit="$/kWh")
    def deferrable_load_energy_flow(self) -> list[highs_linear_expression]:
        """Constraint: cumulative absorbed energy can only increase.

        Output: shadow price indicating the marginal value of energy flow constraints.
        """
        return list(self.energy[1:] >= self.energy[:-1])

    @constraint(output=True, unit="$/kWh")
    def deferrable_load_capacity(self) -> list[highs_linear_expression]:
        """Constraint: absorbed energy cannot exceed the opened capacity.

        Live telemetry can report more energy already absorbed than the
        schedule planned for (e.g. an EV that drove further than forecast),
        so the effective capacity never sits below the initial energy —
        stale telemetry must not make the optimization infeasible.

        Output: shadow price indicating the marginal value of additional capacity.
        """
        return list(self.energy[1:] <= np.maximum(self.capacity[1:], self.initial_energy))

    @constraint(output=True, unit="$/kWh")
    def deferrable_load_requirement(self) -> list[highs_linear_expression]:
        """Constraint: absorbed energy plus deficit covers the requirement.

        Output: shadow price indicating the marginal cost of the requirement.
        """
        return list(self.energy[1:] + self.deficit[1:] >= self.required[1:])

    @constraint
    def deferrable_load_deficit_locked_in(self) -> list[highs_linear_expression]:
        """Constraint: the deficit never shrinks.

        A shortfall at a deadline stays priced even if absorption later
        catches up past the requirement profile.
        """
        return list(self.deficit[1:] >= self.deficit[:-1])

    @constraint
    def deferrable_load_deficit_due(self) -> list[highs_linear_expression]:
        """Constraint: each deficit increment is at most the requirement falling due.

        The due profile is the requirement not already covered by the
        initial energy, made non-decreasing. Its increments sum to at least
        the worst possible shortfall at every boundary, so the requirement
        constraint always stays feasible, while a shortfall can only be
        booked (and priced) at a boundary where requirement actually falls
        due.
        """
        due = np.maximum.accumulate(np.maximum(self.required[1:] - self.initial_energy, 0.0))
        due_increments = np.diff(due, prepend=0.0)
        return list(self.deficit[1:] - self.deficit[:-1] <= due_increments)

    @constraint
    def deferrable_load_overage(self) -> highs_linear_expression:
        """Constraint: overage covers absorption beyond the final requirement.

        Energy already absorbed before the horizon is not overage — an
        overshoot reported by live telemetry is a fact, not a decision to
        price.
        """
        return self.overage[0] >= self.energy[-1] - self._overage_baseline()

    @constraint
    def deferrable_load_overage_limit(self) -> highs_linear_expression:
        """Constraint: overage never exceeds the room absorbable past the requirement."""
        final_capacity = max(float(self.capacity[-1]), self.initial_energy)
        return self.overage[0] <= max(final_capacity - self._overage_baseline(), 0.0)

    def _overage_baseline(self) -> float:
        """Return the absorbed energy beyond which absorption is overage."""
        return max(float(self.required[-1]), self.initial_energy)

    def element_power_produced(self) -> HighspyArray | None:
        """Deferrable loads never produce power."""
        return None

    def element_power_consumed(self) -> HighspyArray:
        """Return power consumed by absorbing energy."""
        return self.power_consumption

    @cost
    def deferrable_load_deficit_cost(self) -> highs_linear_expression:
        """Cost: each deficit increment priced at the boundary where it falls due.

        With a scalar price this telescopes to price times the final deficit.
        """
        require_non_negative("deficit_price", self.deficit_price)
        increments = self.deficit[1:] - self.deficit[:-1]
        return (self.deficit_price[1:] * increments).sum()

    @cost
    def deferrable_load_overage_cost(self) -> highs_linear_expression:
        """Cost: absorption beyond the final requirement priced at overage_price."""
        require_non_negative("overage_price", self.overage_price)
        return self.overage_price * self.overage[0]

    # Output methods

    @output
    def deferrable_load_power(self) -> OutputData:
        """Output: power being consumed to absorb energy."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
        )

    @output
    def deferrable_load_energy_absorbed(self) -> OutputData:
        """Output: cumulative energy absorbed toward the requirement."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self.extract_values(self.energy))

    @output
    def deferrable_load_energy_deficit(self) -> OutputData:
        """Output: locked-in shortfall against the requirement."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self.extract_values(self.deficit))
