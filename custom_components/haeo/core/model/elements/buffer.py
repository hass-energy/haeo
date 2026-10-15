"""Energy or empty space a group of batteries keeps over a window of time.

A buffer is either a reserve or headroom. A reserve is the energy the batteries
must hold to cover the elements' net demand through a grid outage lasting
``window`` hours. Headroom is the mirror image: the empty space the batteries
must keep to absorb the elements' net surplus over the window.

Both are measured from a level, a share of the batteries' capacity: a reserve
from its level up, never below the batteries' min charge, and headroom from its
level down, never above their max charge. With no level set they are measured
from the min or max charge.

At each boundary the requirement is the furthest the running net demand (for a
reserve) or net surplus (for headroom) rises within the following window, the
windowed maximum drawdown of the elements' energy balance. It is measured on the
elements' planned power flows, so elements whose consumption the optimizer
schedules move the requirement with their schedule. Generation counts by what
it could produce, the limit on the power leaving it, so curtailing it in the
plan cannot shrink a headroom that exists to keep room for it.

The windowed maximum is built from fixed-shape rows. Time is cut into blocks
one window long, so every window is the end of one block plus the start of the
next. Running maxima over each block from either end then bound the peak of any
window with a handful of rows per boundary. When the periods or the window
change, rows that no longer apply become free rows, so the LP keeps its shape.

The requirement and the shortfall are measured as energy stored in the
batteries, so a shortfall costs the same per kWh as the batteries hold.
"""

from dataclasses import dataclass
from typing import Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element, NetworkElement
from custom_components.haeo.core.model.linear import INF, LinearArray, Rows
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .battery import Battery
from .connection import Connection
from .segments import EfficiencySegment, PowerLimitSegment

type BufferElementTypeName = Literal["buffer"]
ELEMENT_TYPE: Final[BufferElementTypeName] = "buffer"

# A reserve keeps energy to discharge and headroom keeps space to charge
type BufferKind = Literal["reserve", "headroom"]

type BufferOutputName = Literal[
    "buffer_energy_required",
    "buffer_energy_available",
    "buffer_energy_shortfall",
    "buffer_state_of_charge",
]

BUFFER_OUTPUT_NAMES: Final[frozenset[BufferOutputName]] = frozenset(
    (
        BUFFER_ENERGY_REQUIRED := "buffer_energy_required",
        BUFFER_ENERGY_AVAILABLE := "buffer_energy_available",
        BUFFER_ENERGY_SHORTFALL := "buffer_energy_shortfall",
        BUFFER_STATE_OF_CHARGE := "buffer_state_of_charge",
    )
)

# Tolerance in hours when comparing window ends with boundaries
_TIME_TOLERANCE: Final = 1e-6


class BufferElementConfig(TypedDict):
    """Configuration for creating a Buffer model element."""

    element_type: BufferElementTypeName
    name: str
    kind: BufferKind
    loads: list[str]
    generation: list[str]
    storage: list[str]
    window: float
    level: NDArray[np.float64] | float | None
    price: NDArray[np.float64] | float


@dataclass(frozen=True, slots=True)
class WindowLayout:
    """Where each boundary's window falls, for the current periods and window length.

    Attributes:
        block: Block index of each boundary.
        last: Last boundary inside each boundary's window.
        fraction: How far each window end reaches into the period after ``last``,
            or zero when it ends on a boundary or past the horizon.

    """

    block: NDArray[np.int64]
    last: NDArray[np.int64]
    fraction: NDArray[np.float64]


def window_layout(periods: NDArray[np.float64], window: float) -> WindowLayout:
    """Return where each boundary's window falls for period durations and a window length in hours.

    A window of zero looks no further than its own boundary, so each boundary is its own block.
    """
    times = np.concatenate(([0.0], np.cumsum(periods)))
    if window <= _TIME_TOLERANCE:
        index = np.arange(len(times), dtype=np.int64)
        return WindowLayout(block=index, last=index, fraction=np.zeros(len(times)))
    ends = times + window
    last = np.searchsorted(times, ends + _TIME_TOLERANCE, side="right") - 1
    inside = last < len(periods)
    reach = np.where(inside, ends - times[last], 0.0)
    span = np.where(inside, periods[np.minimum(last, len(periods) - 1)], 1.0)
    fraction = np.where(reach > _TIME_TOLERANCE, reach / span, 0.0)
    block = np.floor(times / window + _TIME_TOLERANCE / window).astype(np.int64)
    return WindowLayout(block=block, last=last.astype(np.int64), fraction=fraction)


def window_peaks(values: NDArray[np.float64], layout: WindowLayout) -> NDArray[np.float64]:
    """Return the largest value within each boundary's window, interpolating at the window end."""
    n_boundaries = len(values)
    index = np.arange(n_boundaries)
    inside = (index[None, :] >= index[:, None]) & (index[None, :] <= layout.last[:, None])
    peaks = np.where(inside, values[None, :], -np.inf).max(axis=1)
    following = values[np.minimum(layout.last + 1, n_boundaries - 1)]
    end = values[layout.last] * (1.0 - layout.fraction) + following * layout.fraction
    return np.where(layout.fraction > 0.0, np.maximum(peaks, end), peaks)


class Buffer(Element[BufferOutputName]):
    """Energy or empty space a group of batteries keeps for a group of elements over a window."""

    window: TrackedParam[float] = TrackedParam()
    level: TrackedParam[NDArray[np.float64] | None] = TrackedParam()
    price: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Solver,
        kind: BufferKind,
        loads: list[NetworkElement[str]],
        generation: list[NetworkElement[str]],
        storage: list[Battery],
        window: float,
        level: NDArray[np.float64] | float | None,
        price: NDArray[np.float64] | float,
    ) -> None:
        """Initialize the buffer over its elements and storage."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=BUFFER_OUTPUT_NAMES)
        n_periods = self.n_periods
        self.kind = kind
        # Headroom tracks the elements' surplus, the negative of their demand
        self._sign = 1.0 if kind == "reserve" else -1.0
        self._loads = loads
        self._generation = generation
        self._storage = storage
        self.window = window
        self.level = broadcast_to_sequence(level, n_periods + 1)
        self.price = broadcast_to_sequence(price, n_periods)

        # Running net demand (or surplus, for headroom) of the elements at each boundary
        self._demand = solver.add_variables(n_periods + 1, name=f"{name}.demand", lower=-INF)
        # Peak demand from each boundary to the end of its block, and from the start of its block
        self._suffix_peak = solver.add_variables(n_periods + 1, name=f"{name}.suffix_peak", lower=-INF)
        self._prefix_peak = solver.add_variables(n_periods + 1, name=f"{name}.prefix_peak", lower=-INF)
        # Stored energy the batteries fall short of the buffer at each boundary after the first
        self._shortfall = solver.add_variables(n_periods, name=f"{name}.shortfall")
        # The solution the required energy was last computed from, and that energy
        self._required: tuple[NDArray[np.float64], NDArray[np.float64]] | None = None

    @property
    def element_names(self) -> list[str]:
        """Return the names of the loads and generation the buffer covers."""
        return [element.name for element in (*self._loads, *self._generation)]

    @property
    def storage_names(self) -> list[str]:
        """Return the names of the batteries that hold the buffer."""
        return [battery.name for battery in self._storage]

    def _layout(self) -> WindowLayout:
        return window_layout(self.periods, self.window)

    def _efficiency(self, battery: Battery) -> NDArray[np.float64]:
        """Return the efficiency between a battery and the network, at each boundary.

        It is the efficiency of the connections the battery discharges through
        for a reserve, or charges through for headroom. With several, the lowest
        is taken, so the buffer never counts on more than the worst path gives.
        A battery with none counts without losses.
        """
        n_boundaries = self.n_periods + 1
        connections = battery.outbound_connections if self.kind == "reserve" else battery.inbound_connections
        efficiencies = [
            np.prod(
                [
                    broadcast_to_sequence(segment.efficiency, n_boundaries)
                    for segment in connection.segments.values()
                    if isinstance(segment, EfficiencySegment) and segment.efficiency is not None
                ]
                or [np.ones(n_boundaries)],
                axis=0,
            )
            for connection in connections
            if isinstance(connection, Connection)
        ]
        return np.min(efficiencies, axis=0) if efficiencies else np.ones(n_boundaries)

    def _base(self, battery: Battery) -> NDArray[np.float64]:
        """Return the stored energy the buffer is measured from in a battery, at each boundary.

        A reserve counts energy above its level and headroom space below it,
        never past the battery's own min or max charge.
        """
        if self.kind == "reserve":
            limit = battery.charge_floor
            return limit if self.level is None else np.maximum(limit, self.level * battery.capacity)
        limit = battery.charge_ceiling
        return limit if self.level is None else np.minimum(limit, self.level * battery.capacity)

    def _network_factor(self, battery: Battery) -> NDArray[np.float64]:
        """Return how much energy at the network side each kWh stored in the battery is worth to the buffer."""
        efficiency = self._efficiency(battery)
        return efficiency if self.kind == "reserve" else 1.0 / efficiency

    def _scale(self) -> NDArray[np.float64]:
        """Return the capacity-weighted network-side worth of a stored kWh, at each boundary.

        It converts between the network-side energy the elements need and the
        energy stored in the batteries, exactly for one battery and for
        batteries with the same efficiency.
        """
        capacity = sum((battery.capacity for battery in self._storage), np.zeros(self.n_periods + 1))
        weighted = sum(
            (self._network_factor(battery) * battery.capacity for battery in self._storage),
            np.zeros(self.n_periods + 1),
        )
        return weighted / capacity

    def _available(self) -> LinearArray:
        """Return the network-side energy the storage can provide past its bases, at each boundary."""
        held = [
            (battery.stored_energy - self._base(battery)) * self._network_factor(battery)
            if self.kind == "reserve"
            else (self._base(battery) - battery.stored_energy) * self._network_factor(battery)
            for battery in self._storage
        ]
        return LinearArray.sum_of([LinearArray.zeros(self.n_periods + 1), *held])

    def _available_generation(self) -> NDArray[np.float64]:
        """Return the most the generation can produce in each period.

        It is the sum of the power limits on the connections out of each
        generator, the most the network lets it produce whatever the plan
        curtails. A connection with no limit adds nothing.
        """
        return sum(
            (
                broadcast_to_sequence(segment.max_power, self.n_periods)
                for generator in self._generation
                for connection in generator.outbound_connections
                if isinstance(connection, Connection)
                for segment in connection.segments.values()
                if isinstance(segment, PowerLimitSegment) and segment.max_power is not None
            ),
            np.zeros(self.n_periods),
        )

    def _net_power(self) -> LinearArray:
        """Return the loads' planned power less the generation's available power in each period."""
        net = LinearArray.zeros(self.n_periods)
        for load in self._loads:
            net = net + load.connection_power()
        return net - self._available_generation()

    @constraint
    def buffer_demand_balance(self) -> Rows:
        """Accumulate the elements' net energy demand (or surplus) from zero at the first boundary."""
        demand = self._demand
        return Rows.concat(
            [
                demand[0] == 0.0,
                demand[1:] - demand[:-1] - self._net_power() * (self._sign * self.periods) == 0.0,
            ]
        )

    @constraint
    def buffer_block_peaks(self) -> Rows:
        """Bound the running demand peaks within each block from both ends.

        Links between boundaries in different blocks have no lower bound, so they are free rows.
        """
        block = self._layout().block
        demand, suffix, prefix = self._demand, self._suffix_peak, self._prefix_peak
        same_block = block[:-1] == block[1:]
        return Rows.concat(
            [
                suffix - demand >= 0.0,
                prefix - demand >= 0.0,
                suffix[:-1] - suffix[1:] >= np.where(same_block, 0.0, -INF),
                prefix[1:] - prefix[:-1] >= np.where(same_block, 0.0, -INF),
            ]
        )

    @constraint
    def buffer_requirement(self) -> Rows:
        """Hold enough for the peak demand within each boundary's window.

        Each boundary after the first has three rows: the rest of its own block,
        the start of the next block up to the window end, and the window end
        itself when it falls inside a period. The window end interpolates between
        the last boundary inside the window and the next one. Rows that do not
        apply have no lower bound, so they are free.
        """
        layout = self._layout()
        demand = self._demand
        last = layout.last[1:]
        fraction = layout.fraction[1:]
        held = self._available()[1:] + self._shortfall * self._scale()[1:] + demand[1:]
        end_next = np.minimum(last + 1, self.n_periods)
        end_demand = demand[last] * (1.0 - fraction) + demand[end_next] * fraction

        return Rows.concat(
            [
                held - self._suffix_peak[1:] >= 0.0,
                held - self._prefix_peak[last] >= np.where(layout.block[last] != layout.block[1:], 0.0, -INF),
                held - end_demand >= np.where(fraction > 0.0, 0.0, -INF),
            ]
        )

    @cost
    def buffer_shortfall_cost(self) -> LinearArray:
        """Charge a holding cost for each stored kWh the batteries fall short of the buffer, per hour."""
        return (self._shortfall * (self.price * self.periods)).total()

    def _required_values(self) -> NDArray[np.float64]:
        """Return the stored energy the buffer requires past its bases, from the solved demand.

        It is computed once per solution, so every output reads the same values.
        """
        solution = self._solver.column_values()
        if self._required is None or self._required[0] is not solution:
            demand = self._demand.value(solution)
            self._required = (solution, (window_peaks(demand, self._layout()) - demand) / self._scale())
        return self._required[1]

    @output
    def buffer_energy_required(self) -> OutputData:
        """Output: stored energy the batteries should hold (or keep free) past their bases at each boundary."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=tuple(self._required_values().tolist()))

    @output
    def buffer_energy_available(self) -> OutputData:
        """Output: stored energy the batteries hold (or keep free) past their bases at each boundary."""
        available = np.asarray(self.extract_values(self._available()), dtype=float) / self._scale()
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=tuple(available.tolist()))

    @output
    def buffer_energy_shortfall(self) -> OutputData:
        """Output: stored energy the batteries fall short of the buffer at each boundary."""
        shortfall = np.concatenate(([0.0], np.asarray(self.extract_values(self._shortfall), dtype=float)))
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=tuple(shortfall.tolist()))

    @output
    def buffer_state_of_charge(self) -> OutputData:
        """Output: the combined state of charge the batteries should stay above, or below for headroom."""
        capacity = sum((battery.capacity for battery in self._storage), np.zeros(self.n_periods + 1))
        base = sum((self._base(battery) for battery in self._storage), np.zeros(self.n_periods + 1))
        required = self._required_values()
        line = base + required if self.kind == "reserve" else base - required
        ratio = np.clip(line / capacity, 0.0, 1.0)
        return OutputData(
            type=OutputType.STATE_OF_CHARGE,
            unit="%",
            values=tuple(ratio.tolist()),
            direction="+" if self.kind == "reserve" else "-",
        )


__all__ = [
    "BUFFER_ENERGY_AVAILABLE",
    "BUFFER_ENERGY_REQUIRED",
    "BUFFER_ENERGY_SHORTFALL",
    "BUFFER_OUTPUT_NAMES",
    "BUFFER_STATE_OF_CHARGE",
    "ELEMENT_TYPE",
    "Buffer",
    "BufferElementConfig",
    "BufferElementTypeName",
    "BufferKind",
    "BufferOutputName",
    "WindowLayout",
    "window_layout",
    "window_peaks",
]
