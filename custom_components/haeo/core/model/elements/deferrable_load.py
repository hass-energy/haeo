"""Deferrable load entity for electrical system modeling.

A deferrable load receives energy only inside scheduled windows (e.g.
calendar events). Each event has its own requirement and its own start and
end, and overlapping events share one window. A single energy accumulator
counts the energy delivered since the window started.

Inside a window the accumulator must stay within a band. Its lower edge is
the energy due: the requirements of the events that have ended. Its upper
edge is the energy started: the requirements of the events that have begun.
Falling below the band is shortfall, priced at the deficit price where an
event is missed, and rising above it is overage, priced at the overage price
where its window ends. Neither is ever forbidden,
so the optimization stays feasible when a requirement physically cannot be
met and when the device has already run past it.

The problem shape never depends on the number of events: every variable and
constraint is sized by the horizon, and events only change parameter values.
"""

from typing import Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, NetworkElement
from custom_components.haeo.core.model.linear import LinearArray, Rows
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, computed, constraint, cost, output
from custom_components.haeo.core.model.solver import Solver

# Model element type for deferrable loads
ELEMENT_TYPE: Final = "deferrable_load"
type DeferrableLoadElementTypeName = Literal["deferrable_load"]

# Type for deferrable load constraint names (shadow prices exposed as outputs)
type DeferrableLoadConstraintName = Literal[
    "element_power_balance",
    "deferrable_load_requirement",
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
    )
)


class DeferrableLoadElementConfig(TypedDict):
    """Configuration for DeferrableLoad model elements."""

    element_type: DeferrableLoadElementTypeName
    name: str
    in_window: NDArray[np.float64]
    window_start: NDArray[np.float64]
    opened: NDArray[np.float64]
    due: NDArray[np.float64]
    deficit_price: NDArray[np.float64]
    overage_price: NDArray[np.float64]
    initial_energy: NotRequired[float]
    is_source: Literal[False]
    is_sink: Literal[True]
    inbound_tags: NotRequired[set[int] | None]


class DeferrableLoad(NetworkElement[DeferrableLoadOutputName]):
    """Deferrable load entity for electrical system modeling.

    The window structure and events are described over the horizon:

    - ``in_window`` (per period): 1 where the period lies inside a window.
      Power is zero in every other period.
    - ``window_start`` (per boundary): 1 where a window starts, resetting
      the accumulator. It separates windows that touch end to start.
    - ``opened`` (per boundary): the requirements of the events starting at
      each boundary. An event already open at the horizon start opens at
      boundary 0.
    - ``due`` (per boundary): the requirements of the events ending at each
      boundary. An event running past the horizon end is due at the final
      boundary, clamped to the horizon.

    Within a window, the energy started by boundary ``k`` is the sum of the
    events opened before ``k``, and the energy due by ``k`` is the sum of the
    events due by ``k``. The accumulator, less any overage, must reach the
    energy due, and anything above the energy started is overage. Shortfall
    and overage never shrink within a window, so a missed deadline stays
    missed and energy delivered before an event starts never counts toward
    it. Shortfall only grows where an event is due, by at most its
    requirement, and is priced there. Overage is priced once, at its
    window's end, so booking it at a cheaper boundary gains nothing.

    The band is exact when events do not nest, that is when an event that
    starts later also ends later. An event nested inside another still gets
    its share of the window's energy by its end, but that energy may arrive
    before it starts.

    ``initial_energy`` is the energy already delivered to the window open at
    the horizon start. It seeds the accumulator for that window only, and an
    overshoot is overage like any other: a fixed cost that changes no
    decision.

    The requirements, initial energy, and prices are never negative.
    """

    # Parameters
    in_window: TrackedParam[NDArray[np.float64]] = TrackedParam()
    window_start: TrackedParam[NDArray[np.float64]] = TrackedParam()
    opened: TrackedParam[NDArray[np.float64]] = TrackedParam()
    due: TrackedParam[NDArray[np.float64]] = TrackedParam()
    initial_energy: TrackedParam[float] = TrackedParam()
    deficit_price: TrackedParam[NDArray[np.float64]] = TrackedParam()
    overage_price: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        in_window: NDArray[np.float64],
        window_start: NDArray[np.float64],
        opened: NDArray[np.float64],
        due: NDArray[np.float64],
        deficit_price: NDArray[np.float64],
        overage_price: NDArray[np.float64],
        initial_energy: float = 0.0,
        is_source: Literal[False] = False,
        is_sink: Literal[True] = True,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a deferrable load entity.

        A deferrable load only consumes, which ``is_source`` and ``is_sink``
        declare for policy compilation and buffer roles.
        """
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=DEFERRABLE_LOAD_OUTPUT_NAMES,
            is_source=is_source,
            is_sink=is_sink,
            inbound_tags=inbound_tags,
        )
        n_periods = self.n_periods

        self.in_window = in_window
        self.window_start = window_start
        self.opened = opened
        self.due = due
        self.initial_energy = initial_energy
        self.deficit_price = deficit_price
        self.overage_price = overage_price

        # Energy delivered in the current window, at every boundary
        self.energy = solver.add_variables(n_periods + 1, name=f"{name}.energy")
        # Energy due but not delivered, at boundaries 1..T
        self.shortfall = solver.add_variables(n_periods, name=f"{name}.shortfall")
        # Energy delivered beyond what has started, at boundaries 1..T
        self.overage = solver.add_variables(n_periods, name=f"{name}.overage")

    @property
    def power_consumption(self) -> LinearArray:
        """Power being consumed by the load.

        Computed on-demand so that accessing self.periods triggers dependency
        tracking when called from within @constraint or @cost decorated methods.
        """
        return self.delivered * (1.0 / self.periods)

    @property
    def delivered(self) -> LinearArray:
        """Energy delivered during each period: the accumulator's step, which restarts at window starts."""
        return self.energy[1:] - self._carry() * self.energy[:-1]

    @computed
    def _carry(self) -> NDArray[np.float64]:
        """Return 1 for each period that continues the window of the boundary before it.

        A period carries the accumulator forward when it is inside a window
        and no window starts at its opening boundary. Every other period
        starts the accumulator from zero.
        """
        return self.in_window * (1.0 - self.window_start[:-1])

    @computed
    def _window_end(self) -> NDArray[np.float64]:
        """Return 1 at boundaries 1..T where a window ends."""
        next_continues = np.append(self._carry()[1:], 0.0)
        return self.in_window * (1.0 - next_continues)

    def _window_total(self, values: NDArray[np.float64]) -> NDArray[np.float64]:
        """Return the running total of per-period values since each period's window started."""
        totals = np.cumsum(values)
        starts = np.flatnonzero(self._carry() <= 0.0)
        last_start = np.zeros(len(values), dtype=np.intp)
        last_start[starts] = starts
        last_start = np.maximum.accumulate(last_start)
        return totals - (totals - values)[last_start]

    @computed
    def _due_at(self) -> NDArray[np.float64]:
        """Return the requirements of the events due at boundaries 1..T, inside windows."""
        return self.in_window * self.due[1:]

    @computed
    def _started(self) -> NDArray[np.float64]:
        """Return the energy started by boundaries 1..T: the events opened in the window so far."""
        return self._window_total(self.in_window * self.opened[:-1])

    @computed
    def _due_by(self) -> NDArray[np.float64]:
        """Return the energy due by boundaries 1..T: the events ended in the window so far."""
        return self._window_total(self._due_at())

    @constraint
    def deferrable_load_initial_energy(self) -> Rows:
        """Constraint: the accumulator starts at the energy already delivered.

        The initial energy only applies when the first period continues an
        open window; otherwise the accumulator starts from zero.
        """
        return self.energy[0] == self._carry()[0] * self.initial_energy

    @constraint
    def deferrable_load_delivery(self) -> Rows:
        """Constraint: energy is never taken back out, so the accumulator only grows within a window."""
        return self.delivered >= 0.0

    @constraint
    def deferrable_load_window(self) -> Rows:
        """Constraint: no energy is delivered outside windows."""
        return (1.0 - self.in_window) * self.delivered <= 0.0

    @constraint(output=True, unit="$/kWh")
    def deferrable_load_requirement(self) -> Rows:
        """Constraint: delivered energy, less overage, plus shortfall reaches the energy due.

        Output: shadow price indicating the marginal cost of requiring one more kWh.
        """
        return self.energy[1:] - self.overage + self.shortfall >= self._due_by()

    @constraint
    def deferrable_load_started(self) -> Rows:
        """Constraint: delivered energy beyond the energy started is overage."""
        return self.energy[1:] - self.overage <= self._started()

    @constraint
    def deferrable_load_shortfall_growth(self) -> Rows:
        """Constraint: shortfall only grows where an event is due, by at most its requirement.

        A boundary where nothing is due can then carry no shortfall that a
        later event's miss would otherwise go unpriced against.
        """
        due_at = self._due_at()
        return Rows.concat(
            [
                self.shortfall[:1] <= due_at[:1],
                self.shortfall[1:] - self._carry()[1:] * self.shortfall[:-1] <= due_at[1:],
            ]
        )

    @constraint
    def deferrable_load_overage_limit(self) -> Rows:
        """Constraint: overage never exceeds the energy delivered, keeping it bounded where unpriced."""
        return self.overage - self.energy[1:] <= 0.0

    @constraint
    def deferrable_load_shortfall_kept(self) -> Rows:
        """Constraint: within a window, a shortfall never shrinks, so a missed deadline stays missed."""
        return self.shortfall[1:] - self._carry()[1:] * self.shortfall[:-1] >= 0.0

    @constraint
    def deferrable_load_overage_kept(self) -> Rows:
        """Constraint: within a window, overage never shrinks, so it never counts toward a later event."""
        return self.overage[1:] - self._carry()[1:] * self.overage[:-1] >= 0.0

    def element_power_produced(self) -> LinearArray | None:
        """Deferrable loads never produce power."""
        return None

    def element_power_consumed(self) -> LinearArray:
        """Return power consumed by the load."""
        return self.power_consumption

    @cost
    def deferrable_load_shortfall_cost(self) -> LinearArray:
        """Cost: each kWh of shortfall priced at the boundary where its event is due."""
        price = self.deficit_price
        return (price[1:] * self.shortfall).total() - (price[2:] * self._carry()[1:] * self.shortfall[:-1]).total()

    @cost
    def deferrable_load_overage_cost(self) -> LinearArray:
        """Cost: each window's overage priced once, at the boundary where the window ends."""
        return (self._window_end() * self.overage_price[1:] * self.overage).total()

    # Output methods

    def _growth_values(self, slack: LinearArray) -> tuple[float, ...]:
        """Return a slack's growth at each boundary, zero at boundary 0."""
        values = np.asarray(self.extract_values(slack), dtype=np.float64)
        growth = values - np.concatenate(([0.0], self._carry()[1:] * values[:-1]))
        return (0.0, *(float(v) for v in np.maximum(growth, 0.0)))

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
        """Output: energy missed at each boundary."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self._growth_values(self.shortfall))

    @output
    def deferrable_load_energy_overage(self) -> OutputData:
        """Output: energy delivered beyond what has started, at each boundary."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=self._growth_values(self.overage))
