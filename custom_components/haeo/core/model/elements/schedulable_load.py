"""Schedulable load entity for electrical system modeling.

A schedulable load runs a fixed power profile once per scheduled window. The
optimizer chooses which boundary inside the window the run starts at, and once
started the run continues to completion: the whole profile must fit between
the start and the window end.

The profile is a sequence of steps, each a duration and a constant power. A
load with a single power and run time is a one-step profile; appliances with
several phases (heat, wash, dry) are longer profiles. Starting at boundary
``b`` places the profile's energy into the periods it overlaps, so each start
is a column of energy per period, and the load's energy is the start weights
times those columns.

A run already in progress at the horizon start is committed: the rest of its
profile is consumed from the horizon start regardless of the plan, and no new
run can start until it finishes.

Each window must receive one run, settled at its end boundary. A missed run is
priced per kWh of the profile's energy rather than enforced, which keeps the
optimization feasible when no start fits. Integer start weights are optional:
the start columns form a consecutive-ones structure that the linear relaxation
often solves integrally, and making only the first start binary keeps the
decision to start now crisp at almost no cost.

The problem shape never depends on the windows or the profile: every variable
and constraint is sized by the horizon, and windows and profile only change
parameter values and coefficients.
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
from custom_components.haeo.core.model.util import broadcast_to_sequence, window_carry, window_end, window_end_index

# Model element type for schedulable loads
ELEMENT_TYPE: Final = "schedulable_load"
type SchedulableLoadElementTypeName = Literal["schedulable_load"]

# Which start weights are integer
type IntegerMode = Literal["none", "first", "all"]
INTEGER_MODES: Final[tuple[IntegerMode, ...]] = ("none", "first", "all")

# Tolerance for comparing times in hours
_TIME_EPSILON: Final = 1e-9

# Type for schedulable load constraint names (shadow prices exposed as outputs)
type SchedulableLoadConstraintName = Literal[
    "element_power_balance",
    "schedulable_load_profile",
]

# Type for all schedulable load output names (union of base outputs and constraints)
type SchedulableLoadOutputName = (
    Literal[
        "schedulable_load_power",
        "schedulable_load_start",
        "schedulable_load_energy_missed",
    ]
    | SchedulableLoadConstraintName
)

# All schedulable load output names (includes constraint shadow prices)
SCHEDULABLE_LOAD_OUTPUT_NAMES: Final[frozenset[SchedulableLoadOutputName]] = frozenset(
    (
        # Base outputs
        SCHEDULABLE_LOAD_POWER := "schedulable_load_power",
        SCHEDULABLE_LOAD_START := "schedulable_load_start",
        SCHEDULABLE_LOAD_ENERGY_MISSED := "schedulable_load_energy_missed",
        # Constraint shadow prices
        SCHEDULABLE_LOAD_POWER_BALANCE := ELEMENT_POWER_BALANCE,
        SCHEDULABLE_LOAD_PROFILE := "schedulable_load_profile",
    )
)


class SchedulableLoadElementConfig(TypedDict):
    """Configuration for SchedulableLoad model elements."""

    element_type: SchedulableLoadElementTypeName
    name: str
    profile_power: NDArray[np.float64]
    profile_duration: NDArray[np.float64]
    in_window: NDArray[np.float64] | float
    window_start: NDArray[np.float64] | float
    deficit_price: NDArray[np.float64] | float
    elapsed: NotRequired[float | None]
    window_started: NotRequired[bool]
    integer_mode: NotRequired[IntegerMode]
    is_source: Literal[False]
    is_sink: Literal[True]
    inbound_tags: NotRequired[set[int] | None]


class SchedulableLoad(NetworkElement[SchedulableLoadOutputName]):
    """Schedulable load entity for electrical system modeling.

    Windows use the same masks as the deferrable load: ``in_window`` per
    period and ``window_start`` per boundary. A start at boundary ``b`` is
    allowed when period ``b`` is inside a window, the whole profile fits
    before that window's end, and no committed run is still in progress.

    ``elapsed`` is how long (hours) the run in progress at the horizon start
    has been running, or None when the load is idle. ``window_started`` says
    the window open at the horizon start already had its run start, whether
    that run is still in progress or has finished; that window then needs no
    further run.

    ``deficit_price`` prices a missed run per kWh of the profile's energy at
    the window's end boundary. The profile and prices are never negative.
    """

    # Parameters
    profile_power: TrackedParam[NDArray[np.float64]] = TrackedParam()
    profile_duration: TrackedParam[NDArray[np.float64]] = TrackedParam()
    in_window: TrackedParam[NDArray[np.float64] | float] = TrackedParam()
    window_start: TrackedParam[NDArray[np.float64] | float] = TrackedParam()
    deficit_price: TrackedParam[NDArray[np.float64] | float] = TrackedParam()
    elapsed: TrackedParam[float | None] = TrackedParam()
    window_started: TrackedParam[bool] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        profile_power: NDArray[np.float64],
        profile_duration: NDArray[np.float64],
        in_window: NDArray[np.float64] | float,
        window_start: NDArray[np.float64] | float,
        deficit_price: NDArray[np.float64] | float,
        elapsed: float | None = None,
        window_started: bool = False,
        integer_mode: IntegerMode = "first",
        is_source: Literal[False] = False,
        is_sink: Literal[True] = True,
        inbound_tags: set[int] | None = None,
    ) -> None:
        """Initialize a schedulable load entity.

        A schedulable load only consumes, which ``is_source`` and ``is_sink``
        declare for policy compilation and buffer roles.
        """
        super().__init__(
            name=name,
            periods=periods,
            solver=solver,
            output_names=SCHEDULABLE_LOAD_OUTPUT_NAMES,
            is_source=is_source,
            is_sink=is_sink,
            inbound_tags=inbound_tags,
        )
        n_periods = self.n_periods

        self.profile_power = np.asarray(profile_power, dtype=np.float64)
        self.profile_duration = np.asarray(profile_duration, dtype=np.float64)
        self.in_window = broadcast_to_sequence(in_window, n_periods)
        self.window_start = broadcast_to_sequence(window_start, n_periods + 1)
        self.deficit_price = broadcast_to_sequence(deficit_price, n_periods + 1)
        self.elapsed = elapsed
        self.window_started = window_started

        # Which start weights are integer is structural: it decides whether
        # the network solves a MIP, so it is fixed when the element is built.
        self.integer_mode: IntegerMode = integer_mode

        # Weight of the run starting at each boundary 0..T-1
        self.start = solver.add_variables(n_periods, name=f"{name}.start", upper=1.0)
        # Energy consumed during each period
        self.energy = solver.add_variables(n_periods, name=f"{name}.energy")
        # Runs started in the current window, at every boundary
        self.runs = solver.add_variables(n_periods + 1, name=f"{name}.runs")
        # Run missed by the window ending at boundaries 1..T
        self.missed = solver.add_variables(n_periods, name=f"{name}.missed")

    def integer_variables(self) -> LinearArray | None:
        """Return the start weights the integer mode makes binary."""
        if self.integer_mode == "all":
            return self.start
        if self.integer_mode == "first":
            return self.start[:1]
        return None

    @property
    def power_consumption(self) -> LinearArray:
        """Power being consumed by the load.

        Computed on-demand so that accessing self.periods triggers dependency
        tracking when called from within @constraint or @cost decorated methods.
        """
        return self.energy * (1.0 / self.periods)

    # Window and profile geometry

    def _in_window(self) -> NDArray[np.float64]:
        """Return the per-period window flag.

        A parameter update can set a plain float, as the model config allows.
        """
        return broadcast_to_sequence(self.in_window, self.n_periods)

    def _boundaries_of(self, value: NDArray[np.float64] | float) -> NDArray[np.float64]:
        """Broadcast a per-boundary parameter to every boundary.

        A parameter update can set a plain float, as the model config allows.
        """
        return broadcast_to_sequence(value, self.n_periods + 1)

    def _carry(self) -> NDArray[np.float64]:
        """Return 1 for each period that continues the window of the boundary before it."""
        return window_carry(self._in_window(), self._boundaries_of(self.window_start))

    def _window_end(self) -> NDArray[np.float64]:
        """Return 1 at boundaries 1..T where a window ends."""
        return window_end(self._in_window(), self._boundaries_of(self.window_start))

    def _boundaries(self) -> NDArray[np.float64]:
        """Return the time of each boundary in hours from the horizon start."""
        return np.concatenate(([0.0], np.cumsum(self.periods)))

    def _profile_knots(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return the profile's cumulative time and cumulative energy at each step edge."""
        durations = self.profile_duration
        cumulative_time = np.concatenate(([0.0], np.cumsum(durations)))
        cumulative_energy = np.concatenate(([0.0], np.cumsum(self.profile_power * durations)))
        return cumulative_time, cumulative_energy

    def _run_energy(self, since_start: NDArray[np.float64]) -> NDArray[np.float64]:
        """Return the profile energy consumed by each time since the run started.

        Times before the start consume nothing and times after the end
        consume the whole profile.
        """
        cumulative_time, cumulative_energy = self._profile_knots()
        return np.interp(since_start, cumulative_time, cumulative_energy)

    def _run_duration(self) -> float:
        """Return how long one run of the profile takes, in hours."""
        return float(np.sum(self.profile_duration))

    def _run_total_energy(self) -> float:
        """Return the energy one run of the profile consumes, in kWh."""
        return float(np.sum(self.profile_power * self.profile_duration))

    def _start_columns(self) -> NDArray[np.float64]:
        """Return the energy each start places in each period.

        Entry ``[t, b]`` is the energy consumed in period ``t`` by a run
        starting at boundary ``b``. Runs only reach forward in time, so the
        matrix is lower triangular, and a run past the horizon end is cut off
        there.
        """
        boundaries = self._boundaries()
        since_start = boundaries[:, None] - boundaries[None, :-1]
        cumulative = self._run_energy(since_start)
        return cumulative[1:] - cumulative[:-1]

    def _committed_energy(self) -> NDArray[np.float64]:
        """Return the energy the run in progress still consumes in each period."""
        if self.elapsed is None:
            return np.zeros(self.n_periods)
        cumulative = self._run_energy(self.elapsed + self._boundaries())
        return cumulative[1:] - cumulative[:-1]

    def _committed_until(self) -> float:
        """Return when the run in progress finishes, in hours from the horizon start."""
        if self.elapsed is None:
            return 0.0
        return max(self._run_duration() - self.elapsed, 0.0)

    def _allowed_starts(self) -> NDArray[np.float64]:
        """Return 1 for each boundary 0..T-1 where a run may start.

        A run may start inside a window when its whole profile fits before
        that window's end and the committed run has finished.
        """
        boundaries = self._boundaries()
        starts = boundaries[:-1]
        in_window = self._in_window()
        window_end_time = boundaries[window_end_index(in_window, self._boundaries_of(self.window_start))]
        fits = starts + self._run_duration() <= window_end_time + _TIME_EPSILON
        free = starts >= self._committed_until() - _TIME_EPSILON
        return in_window * fits * free

    # Constraints

    @constraint(output=True, unit="$/kWh")
    def schedulable_load_profile(self) -> Rows:
        """Constraint: each period's energy is what the chosen starts and the committed run consume there.

        Output: shadow price indicating the marginal cost of energy in each period.
        """
        return self.energy - self._start_columns() @ self.start == self._committed_energy()

    @constraint
    def schedulable_load_start_allowed(self) -> Rows:
        """Constraint: runs only start where the profile fits inside a window."""
        return self.start <= self._allowed_starts()

    @constraint
    def schedulable_load_initial_runs(self) -> Rows:
        """Constraint: the window open at the horizon start counts a run it already started."""
        return self.runs[0] == self._carry()[0] * float(self.window_started)

    @constraint
    def schedulable_load_run_count(self) -> Rows:
        """Constraint: the run count adds each start, resetting at window starts."""
        return self.runs[1:] - self._carry() * self.runs[:-1] - self.start == 0.0

    @constraint
    def schedulable_load_one_run(self) -> Rows:
        """Constraint: each window receives one run, or books it as missed.

        At a window end the runs counted plus the missed run equal one, so at
        most one run starts per window. Away from window ends the missed run
        is pinned to zero.
        """
        ends = self._window_end()
        return ends * self.runs[1:] + self.missed == ends

    def element_power_produced(self) -> LinearArray | None:
        """Schedulable loads never produce power."""
        return None

    def element_power_consumed(self) -> LinearArray:
        """Return power consumed by the load."""
        return self.power_consumption

    @cost
    def schedulable_load_missed_cost(self) -> LinearArray:
        """Cost: each missed run priced per kWh of the profile at its window end."""
        deficit_price = self._boundaries_of(self.deficit_price)
        return (self.missed * (deficit_price[1:] * self._run_total_energy())).total()

    # Output methods

    @output
    def schedulable_load_power(self) -> OutputData:
        """Output: power consumed by the load."""
        return OutputData(
            type=OutputType.POWER, unit="kW", values=self.extract_values(self.power_consumption), direction="-"
        )

    @output
    def schedulable_load_start(self) -> OutputData:
        """Output: weight of the run starting at each boundary, 1 for a planned start."""
        values = (*self.extract_values(self.start), 0.0)
        return OutputData(type=OutputType.AVAILABILITY, unit=None, values=values)

    @output
    def schedulable_load_energy_missed(self) -> OutputData:
        """Output: profile energy of the runs missed by each window, at its end boundary."""
        total = self._run_total_energy()
        values = (0.0, *(total * missed for missed in self.extract_values(self.missed)))
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=values)
