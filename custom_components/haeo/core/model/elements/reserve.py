"""Energy or empty space shared by a group of batteries over a window of time.

A reserve is the energy the batteries must hold to cover the elements' net
demand through a grid outage lasting ``window`` hours. Headroom is the mirror
image: the empty space the batteries must keep to absorb the elements' net
surplus over the window. Each also holds a fixed ``minimum`` on top.

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
"""

from dataclasses import dataclass
from typing import Final, Literal, TypedDict

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element, NetworkElement
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import TrackedParam, constraint, cost, output
from custom_components.haeo.core.model.util import broadcast_to_sequence

from .battery import Battery
from .connection import Connection
from .segments import EfficiencySegment, PowerLimitSegment

type ReserveElementTypeName = Literal["reserve"]
ELEMENT_TYPE: Final[ReserveElementTypeName] = "reserve"

# A reserve keeps energy to discharge and headroom keeps space to charge
type ReserveKind = Literal["reserve", "headroom"]

type ReserveOutputName = Literal[
    "reserve_energy_required",
    "reserve_energy_available",
    "reserve_energy_shortfall",
]

RESERVE_OUTPUT_NAMES: Final[frozenset[ReserveOutputName]] = frozenset(
    (
        RESERVE_ENERGY_REQUIRED := "reserve_energy_required",
        RESERVE_ENERGY_AVAILABLE := "reserve_energy_available",
        RESERVE_ENERGY_SHORTFALL := "reserve_energy_shortfall",
    )
)

# Tolerance in hours when comparing window ends with boundaries
_TIME_TOLERANCE: Final = 1e-6


class ReserveElementConfig(TypedDict):
    """Configuration for creating a Reserve model element."""

    element_type: ReserveElementTypeName
    name: str
    kind: ReserveKind
    loads: list[str]
    generation: list[str]
    storage: list[str]
    window: float
    minimum: NDArray[np.float64] | float
    price: NDArray[np.float64] | float


@dataclass(frozen=True, slots=True)
class ReserveStorage:
    """A battery holding the requirement and the connection the requirement flows through.

    For a reserve this is the connection the battery discharges through, and for
    headroom the one it charges through.
    """

    battery: Battery
    connection: Connection[str]


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
    """Return where each boundary's window falls for period durations and a window length in hours."""
    times = np.concatenate(([0.0], np.cumsum(periods)))
    ends = times + window
    last = np.searchsorted(times, ends + _TIME_TOLERANCE, side="right") - 1
    inside = last < len(periods)
    reach = np.where(inside, ends - times[last], 0.0)
    span = np.where(inside, periods[np.minimum(last, len(periods) - 1)], 1.0)
    fraction = np.where(reach > _TIME_TOLERANCE, reach / span, 0.0)
    block = np.floor(times / window + _TIME_TOLERANCE / window).astype(np.int64)
    return WindowLayout(block=block, last=last.astype(np.int64), fraction=fraction)


class Reserve(Element[ReserveOutputName]):
    """Energy or empty space a group of batteries must hold for a group of elements over a window."""

    window: TrackedParam[float] = TrackedParam()
    minimum: TrackedParam[NDArray[np.float64]] = TrackedParam()
    price: TrackedParam[NDArray[np.float64]] = TrackedParam()

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        *,
        solver: Highs,
        kind: ReserveKind,
        loads: list[NetworkElement[str]],
        generation: dict[str, list[PowerLimitSegment]],
        storage: list[ReserveStorage],
        window: float,
        minimum: NDArray[np.float64] | float,
        price: NDArray[np.float64] | float,
    ) -> None:
        """Initialize the requirement over its elements and storage."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=RESERVE_OUTPUT_NAMES)
        n_periods = self.n_periods
        self.kind = kind
        # Headroom tracks the elements' surplus, the negative of their demand
        self._sign = 1.0 if kind == "reserve" else -1.0
        self._loads = loads
        self._generation = generation
        self._storage = storage
        self.window = window
        self.minimum = broadcast_to_sequence(minimum, n_periods + 1)
        self.price = broadcast_to_sequence(price, n_periods)

        # Running net demand (or surplus, for headroom) of the elements at each boundary
        self._demand = solver.addVariables(n_periods + 1, lb=-np.inf, name_prefix=f"{name}_demand_", out_array=True)
        # Peak demand from each boundary to the end of its block, and from the start of its block
        self._suffix_peak = solver.addVariables(
            n_periods + 1, lb=-np.inf, name_prefix=f"{name}_suffix_", out_array=True
        )
        self._prefix_peak = solver.addVariables(
            n_periods + 1, lb=-np.inf, name_prefix=f"{name}_prefix_", out_array=True
        )
        # Energy the storage falls short of the reserve at each boundary after the first
        self._shortfall = solver.addVariables(n_periods, lb=0.0, name_prefix=f"{name}_shortfall_", out_array=True)

    @property
    def element_names(self) -> list[str]:
        """Return the names of the loads and generation the requirement covers."""
        return [*(load.name for load in self._loads), *self._generation]

    @property
    def storage_names(self) -> list[str]:
        """Return the names of the batteries that hold the reserve."""
        return [storage.battery.name for storage in self._storage]

    def _layout(self) -> WindowLayout:
        return window_layout(self.periods, self.window)

    def _available(self) -> list[highs_linear_expression | float]:
        """Return what the storage can provide at each boundary, measured at the network side.

        A reserve counts the stored energy the batteries can deliver after
        discharge losses. Headroom counts the energy the batteries can absorb
        into their empty space before charge losses.
        """
        n_boundaries = self.n_periods + 1
        available: list[highs_linear_expression | float] = [0.0] * n_boundaries
        for storage in self._storage:
            efficiency = np.ones(n_boundaries)
            for segment in storage.connection.segments.values():
                if isinstance(segment, EfficiencySegment) and segment.efficiency is not None:
                    efficiency = efficiency * broadcast_to_sequence(segment.efficiency, n_boundaries)
            stored = storage.battery.stored_energy
            capacity = storage.battery.capacity
            for index in range(n_boundaries):
                if self.kind == "reserve":
                    held = stored[index] * float(efficiency[index])
                else:
                    held = (float(capacity[index]) - stored[index]) * (1.0 / float(efficiency[index]))
                available[index] = available[index] + held
        return available

    def _net_power(self) -> NDArray[np.object_] | HighspyArray:
        """Return the loads' planned power less the generation's available power in each period."""
        net: NDArray[np.object_] | HighspyArray = np.zeros(self.n_periods, dtype=object)
        for load in self._loads:
            net = net + load.connection_power()
        for limits in self._generation.values():
            available = sum(
                (
                    broadcast_to_sequence(max_power, self.n_periods)
                    for limit in limits
                    if (max_power := limit.max_power) is not None
                ),
                np.zeros(self.n_periods),
            )
            net = net - available
        return net

    @constraint
    def reserve_demand_balance(self) -> list[highs_linear_expression]:
        """Accumulate the elements' net energy demand (or surplus) from zero at the first boundary."""
        demand = self._demand
        net = self._net_power()
        rows = [demand[0] == 0.0]
        rows.extend(
            demand[index + 1] - demand[index] - net[index] * (self._sign * float(duration)) == 0.0
            for index, duration in enumerate(self.periods)
        )
        return rows

    @constraint
    def reserve_block_peaks(self) -> list[highs_linear_expression]:
        """Bound the running demand peaks within each block from both ends."""
        layout = self._layout()
        demand, suffix, prefix = self._demand, self._suffix_peak, self._prefix_peak
        rows = [suffix[index] - demand[index] >= 0.0 for index in range(self.n_periods + 1)]
        rows.extend(prefix[index] - demand[index] >= 0.0 for index in range(self.n_periods + 1))
        for index in range(self.n_periods):
            link = suffix[index] - suffix[index + 1]
            rows.append(link >= 0.0 if layout.block[index] == layout.block[index + 1] else link)
        for index in range(1, self.n_periods + 1):
            link = prefix[index] - prefix[index - 1]
            rows.append(link >= 0.0 if layout.block[index] == layout.block[index - 1] else link)
        return rows

    @constraint
    def reserve_requirement(self) -> list[highs_linear_expression]:
        """Hold enough energy for the peak demand within each boundary's window, plus the minimum.

        Each boundary has three rows: the rest of its own block, the start of the
        next block up to the window end, and the window end itself when it falls
        inside a period. Rows that do not apply are free.
        """
        layout = self._layout()
        demand = self._demand
        available = self._available()
        rows: list[highs_linear_expression] = []
        for index in range(1, self.n_periods + 1):
            held = available[index] + self._shortfall[index - 1] + demand[index]
            minimum = float(self.minimum[index])
            last = int(layout.last[index])
            fraction = float(layout.fraction[index])

            rows.append(held - self._suffix_peak[index] >= minimum)

            prefix_row = held - self._prefix_peak[last]
            rows.append(prefix_row >= minimum if layout.block[last] != layout.block[index] else prefix_row)

            if fraction > 0.0:
                end_demand = demand[last + 1] * fraction
                end_row = (
                    held - demand[index] * fraction - end_demand
                    if last == index
                    else held - demand[last] * (1.0 - fraction) - end_demand
                )
                rows.append(end_row >= minimum)
            else:
                rows.append(held)
        return rows

    @cost
    def reserve_shortfall_cost(self) -> highs_linear_expression:
        """Charge a holding cost for each kWh the storage falls short of the reserve, per hour."""
        return Highs.qsum(self._shortfall * (self.price * self.periods))

    def _demand_values(self) -> NDArray[np.float64]:
        return np.asarray(self.extract_values(self._demand), dtype=float)

    def _required_values(self) -> NDArray[np.float64]:
        """Return the reserve required at each boundary from the solved demand."""
        layout = self._layout()
        demand = self._demand_values()
        times = np.concatenate(([0.0], np.cumsum(self.periods)))
        required = np.empty_like(demand)
        for index, last in enumerate(layout.last):
            peak = float(demand[index : last + 1].max())
            if layout.fraction[index] > 0.0:
                peak = max(peak, float(np.interp(times[index] + self.window, times, demand)))
            required[index] = self.minimum[index] + peak - demand[index]
        return required

    def _available_values(self) -> NDArray[np.float64]:
        return np.asarray(self.extract_values(self._available()), dtype=float)

    @output
    def reserve_energy_required(self) -> OutputData:
        """Output: energy the storage should hold at each boundary."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=tuple(self._required_values().tolist()))

    @output
    def reserve_energy_available(self) -> OutputData:
        """Output: energy the storage can deliver at each boundary."""
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=tuple(self._available_values().tolist()))

    @output
    def reserve_energy_shortfall(self) -> OutputData:
        """Output: energy the storage falls short of the reserve at each boundary."""
        shortfall = np.maximum(self._required_values() - self._available_values(), 0.0)
        return OutputData(type=OutputType.ENERGY, unit="kWh", values=tuple(shortfall.tolist()))


__all__ = [
    "ELEMENT_TYPE",
    "RESERVE_ENERGY_AVAILABLE",
    "RESERVE_ENERGY_REQUIRED",
    "RESERVE_ENERGY_SHORTFALL",
    "RESERVE_OUTPUT_NAMES",
    "Reserve",
    "ReserveElementConfig",
    "ReserveElementTypeName",
    "ReserveKind",
    "ReserveOutputName",
    "ReserveStorage",
    "WindowLayout",
    "window_layout",
]
