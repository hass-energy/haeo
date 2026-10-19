"""Deferrable load entity for electrical system modeling.

A deferrable load absorbs energy only inside scheduled, non-overlapping
windows (e.g. calendar events). A single energy accumulator counts the energy
delivered in the current window: it resets to zero at each window start, and
its value at a window's end boundary is the energy that window received.

Each window's requirement is settled at its end boundary. A shortfall is
priced rather than enforced, which keeps the optimization feasible when the
requirement physically cannot be met. Delivery beyond the requirement is
either forbidden (no overage price) or priced (overage price set).

The problem shape never depends on the number of windows: every variable and
constraint is sized by the horizon, and windows only change parameter values.
"""

from typing import Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, NetworkElement
from custom_components.haeo.core.model.linear import LinearArray, Rows
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.core.model.solver import Solver

# Model element type for deferrable loads
ELEMENT_TYPE: Final = "deferrable_load"
type DeferrableLoadElementTypeName = Literal["deferrable_load"]

# Type for deferrable load constraint names (shadow prices exposed as outputs)
type DeferrableLoadConstraintName = Literal[
    "element_power_balance",
    "deferrable_load_requirement",
    "deferrable_load_cap",
]

# Type for all deferrable load output names (union of base outputs and constraints)
type DeferrableLoadOutputName = (
    Literal[
        "deferrable_load_power",
        "deferrable_load_energy_delivered",
        "deferrable_load_energy_shortfall",
        "deferrable_load_energy_overage",
    ]
    | DeferrableLoadConstraintName
)

# All deferrable load output names (includes constraint shadow prices)
DEFERRABLE_LOAD_OUTPUT_NAMES: Final[frozenset[DeferrableLoadOutputName]] = frozenset(
    (
        # Base outputs
        DEFERRABLE_LOAD_POWER := "deferrable_load_power",
        DEFERRABLE_LOAD_ENERGY_DELIVERED := "deferrable_load_energy_delivered",
        DEFERRABLE_LOAD_ENERGY_SHORTFALL := "deferrable_load_energy_shortfall",
        DEFERRABLE_LOAD_ENERGY_OVERAGE := "deferrable_load_energy_overage",
        # Constraint shadow prices
        DEFERRABLE_LOAD_POWER_BALANCE := ELEMENT_POWER_BALANCE,
        DEFERRABLE_LOAD_REQUIREMENT := "deferrable_load_requirement",
        DEFERRABLE_LOAD_CAP := "deferrable_load_cap",
    )
)


class DeferrableLoadElementConfig(TypedDict):
    """Configuration for DeferrableLoad model elements."""

    element_type: DeferrableLoadElementTypeName
    name: str
    in_window: NDArray[np.float64]
    window_start: NDArray[np.float64]
    requirement: NDArray[np.float64]
    deficit_price: NDArray[np.float64]
    initial_energy: NotRequired[float]
    overage_price: NotRequired[NDArray[np.float64] | None]
    is_source: Literal[False]
    is_sink: Literal[True]
    outbound_tags: NotRequired[set[int] | None]
    inbound_tags: NotRequired[set[int] | None]


class DeferrableLoad(NetworkElement[DeferrableLoadOutputName]):
    """Deferrable load entity for electrical system modeling.

    Window structure is described by three masks over the horizon:

    - ``in_window`` (per period): 1 where the period lies inside a window.
      Power is zero in every other period.
    - ``window_start`` (per boundary): 1 where a window starts, resetting
      the accumulator. It separates windows that touch end to start.
    - ``requirement`` (per boundary): the energy a window must receive,
      placed at its end boundary.

    A window's end boundary is the last boundary of a run of in-window
    periods, or a boundary where the next window starts. A window still
    open at the horizon end therefore settles at the final boundary.

    ``initial_energy`` is the energy already delivered to the window open at
    the horizon start. It seeds the accumulator for that window only. For
    that window, the settled requirement is ``max(requirement,
    initial_energy)``: an overshoot already reported by telemetry is a sunk
    fact, so it is neither priced nor allowed to make the cap infeasible.

    ``in_window`` has one value per period; ``window_start``, ``requirement``,
    and both prices have one per boundary. The requirement, initial energy,
    and prices are never negative: a negative price would reward booking a
    shortfall or overage that never happens.
    """

    # Parameters
    in_window: TrackedParam[NDArray[np.float64]] = TrackedParam()
    window_start: TrackedParam[NDArray[np.float64]] = TrackedParam()
    requirement: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_energy: TrackedParam[float] = TrackedParam()
    deficit_price: TrackedParam[NDArray[np.float64]] = TrackedParam()
    overage_price: TrackedParam[NDArray[np.float64] | None] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        in_window: NDArray[np.float64],
        window_start: NDArray[np.float64],
        requirement: NDArray[np.float64],
        deficit_price: NDArray[np.float64],
        initial_energy: float = 0.0,
        overage_price: NDArray[np.float64] | None = None,
        is_source: Literal[False] = False,  # noqa: ARG002 (declared in the config for policy compilation)
        is_sink: Literal[True] = True,  # noqa: ARG002 (declared in the config for policy compilation)
        outbound_tags: set[int] | None = None,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a deferrable load entity.

        A deferrable load only consumes; its config declares that for policy
        compilation through ``is_source`` and ``is_sink``.
        """
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=DEFERRABLE_LOAD_OUTPUT_NAMES,
            outbound_tags=outbound_tags,
            inbound_tags=inbound_tags,
        )
        n_periods = self.n_periods

        self.in_window = in_window
        self.window_start = window_start
        self.requirement = requirement
        self.initial_energy = initial_energy
        self.deficit_price = deficit_price

        # Whether delivery beyond the requirement is allowed (and priced) is a
        # structural decision made here; the price values update reactively.
        self._has_overage = overage_price is not None
        self.overage_price = overage_price

        # Energy delivered in the current window, at every boundary
        self.energy = solver.add_variables(n_periods + 1, name=f"{name}.energy")
        # Energy delivered during each period
        self.delivered = solver.add_variables(n_periods, name=f"{name}.delivered")
        # Shortfall against the requirement at boundaries 1..T
        self.shortfall = solver.add_variables(n_periods, name=f"{name}.shortfall")
        # Delivery beyond the requirement at boundaries 1..T
        self.overage = solver.add_variables(n_periods, name=f"{name}.overage") if self._has_overage else None

    @property
    def power_consumption(self) -> LinearArray:
        """Power being consumed by the load.

        Computed on-demand so that accessing self.periods triggers dependency
        tracking when called from within @constraint or @cost decorated methods.
        """
        return self.delivered * (1.0 / self.periods)

    def _carry(self) -> NDArray[np.float64]:
        """Return 1 for each period that continues the window of the boundary before it.

        A period carries the accumulator forward when it is inside a window
        and no window starts at its opening boundary. Every other period
        starts the accumulator from zero.
        """
        return self.in_window * (1.0 - self.window_start[:-1])

    def _window_end(self) -> NDArray[np.float64]:
        """Return 1 at boundaries 1..T where a window ends."""
        in_window = self.in_window
        next_in_window = np.append(in_window[1:], 0.0)
        next_continues = next_in_window * (1.0 - self.window_start[1:])
        return in_window * (1.0 - next_continues)

    def _settled_requirement(self) -> NDArray[np.float64]:
        """Return the requirement settled at boundaries 1..T.

        The requirement only counts at window end boundaries. The window
        open at the horizon start settles against at least its initial
        energy, so a sunk telemetry overshoot is neither priced nor capped.
        """
        window_end = self._window_end()
        settled = window_end * self.requirement[1:]
        carry = self._carry()
        if carry[0] > 0.0:
            first_end = int(np.argmax(window_end > 0.0))
            settled[first_end] = max(float(settled[first_end]), self.initial_energy)
        return settled

    @constraint
    def deferrable_load_initial_energy(self) -> Rows:
        """Constraint: the accumulator starts at the energy already delivered.

        The initial energy only applies when the first period continues an
        open window; otherwise the accumulator starts from zero.
        """
        return self.energy[0] == self._carry()[0] * self.initial_energy

    @constraint
    def deferrable_load_accumulation(self) -> Rows:
        """Constraint: the accumulator adds each period's delivery, resetting at window starts."""
        return self.energy[1:] - self._carry() * self.energy[:-1] - self.delivered == 0.0

    @constraint
    def deferrable_load_window(self) -> Rows:
        """Constraint: no energy is delivered outside windows."""
        return (1.0 - self.in_window) * self.delivered <= 0.0

    @constraint(output=True, unit="$/kWh")
    def deferrable_load_requirement(self) -> Rows:
        """Constraint: delivered energy plus shortfall covers the requirement at window ends.

        Output: shadow price indicating the marginal cost of requiring one more kWh.
        """
        window_end = self._window_end()
        return window_end * self.energy[1:] + self.shortfall >= self._settled_requirement()

    @constraint
    def deferrable_load_shortfall_limit(self) -> Rows:
        """Constraint: shortfall never exceeds the settled requirement.

        This pins the shortfall to zero away from window ends and keeps it
        bounded even where it is unpriced.
        """
        return self.shortfall <= self._settled_requirement()

    @constraint(output=True, unit="$/kWh")
    def deferrable_load_cap(self) -> Rows:
        """Constraint: delivery beyond the requirement at window ends is overage.

        Without an overage price there is no overage variable, so delivery
        is capped at the requirement.

        Output: shadow price indicating the marginal value of a higher cap.
        """
        window_end = self._window_end()
        delivered_at_end = window_end * self.energy[1:]
        if self.overage is not None:
            delivered_at_end = delivered_at_end - self.overage
        return delivered_at_end <= self._settled_requirement()

    @constraint
    def deferrable_load_overage_limit(self) -> Rows:
        """Constraint: overage never exceeds the energy delivered at a window end.

        This pins the overage to zero away from window ends and keeps it
        bounded even where it is unpriced.
        """
        if self.overage is None:
            return Rows.concat([])
        return self.overage - self._window_end() * self.energy[1:] <= 0.0

    def element_power_produced(self) -> LinearArray | None:
        """Deferrable loads never produce power."""
        return None

    def element_power_consumed(self) -> LinearArray:
        """Return power consumed by the load."""
        return self.power_consumption

    @cost
    def deferrable_load_shortfall_cost(self) -> LinearArray:
        """Cost: each window's shortfall priced at its end boundary."""
        return (self.deficit_price[1:] * self.shortfall).total()

    @cost
    def deferrable_load_overage_cost(self) -> LinearArray | None:
        """Cost: each window's overage priced at its end boundary."""
        if self.overage is None or self.overage_price is None:
            return None
        return (self.overage_price[1:] * self.overage).total()

    # Output methods

    def _settlement(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return the delivered-minus-requirement gap and window end mask at boundaries 1..T."""
        energy = np.asarray(self.extract_values(self.energy[1:]), dtype=np.float64)
        return energy - self._settled_requirement(), self._window_end()

    @output
    def deferrable_load_power(self) -> OutputData:
        """Output: power consumed by the load."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
        )

    @output
    def deferrable_load_energy_delivered(self) -> OutputData:
        """Output: energy delivered in the current window."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self.extract_values(self.energy))

    @output
    def deferrable_load_energy_shortfall(self) -> OutputData:
        """Output: requirement missed by each window, at its end boundary."""
        gap, window_end = self._settlement()
        values = (0.0, *(float(v) for v in window_end * np.maximum(-gap, 0.0)))
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=values)

    @output
    def deferrable_load_energy_overage(self) -> OutputData:
        """Output: delivery beyond each window's requirement, at its end boundary."""
        gap, window_end = self._settlement()
        values = (0.0, *(float(v) for v in window_end * np.maximum(gap, 0.0)))
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=values)
