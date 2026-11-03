"""Offer curves: how a planned flow responds to its own price.

An offer curve says, for a window of consecutive periods, how much power would
flow on average at each price the window could have, with the price of every
period outside it left as forecast. The window is how long a price change
lasts: the shorter it is, the less it costs the rest of the plan to move
energy into or out of it, so a curve of one short period overstates how a
home responds to a price that holds for a market interval.

Shifting the window's price by ``d`` adds ``d`` times its energy to the cost,
so the cheapest cost as a function of ``d`` is concave and piecewise linear,
and its slope is the planned energy. The flow is therefore a step function of
the price that never rises as the price rises, and its steps are the kinks of
the cost.

The kinks are found by Eisner and Severance's method: solve at the ends of a
price range, and where the two plans' cost lines cross, solve once more. If
that solve costs what the lines say, the crossing is the only kink between
them; otherwise each half is searched the same way. A curve with ``k`` steps
takes ``2k + 1`` solves, each warm-started from the last, and needs no ranging
or basis bookkeeping, so primal degeneracy cannot mislead it.

The solves run on a copy of the solved model, so the plan, its duals and the
basis the next optimization starts from are never touched.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from highspy import HighsModelStatus
import numpy as np
from numpy.typing import NDArray

from .linear import LinearArray
from .solver import Solver, SolverError

# Cost in $ by which a crossing must beat the cost lines to count as another kink
_COST_TOLERANCE: Final = 1e-9
# Power in kW within which two steps of a curve count as the same
_POWER_TOLERANCE: Final = 1e-6
# Kinks searched for before a price range is taken as one step, which only
# numerical noise in the costs can reach
_MAX_DEPTH: Final = 64


@dataclass(frozen=True, slots=True)
class OfferStep:
    """Power that flows from a price shift up to the next step's.

    Attributes:
        price: Shift in $/kWh from the window's forecast prices at which the step starts.
        power: Average power in kW of the flow over the window at prices in the step.

    """

    price: float
    power: float


@dataclass(frozen=True, slots=True)
class OfferCurve:
    """The average power of a flow over a window of periods at every price shift in a range.

    Attributes:
        periods: Indices of the periods in the window.
        steps: Steps in rising price order, the first starting at the bottom of
            the range and each holding until the next one starts. Power falls
            from each step to the next.

    """

    periods: tuple[int, ...]
    steps: tuple[OfferStep, ...]

    def power_at(self, price: float) -> float:
        """Return the power at a price shift, taking the step above when it is on a step's edge."""
        power = self.steps[0].power
        for step in self.steps[1:]:
            if price < step.price:
                break
            power = step.power
        return power


@dataclass(frozen=True, slots=True)
class _Point:
    """A solve at one price shift: its cheapest cost and the energy at that shift."""

    price: float
    cost: float
    energy: float


class _Probe:
    """Solves a copy of a solved model with the price of some energy shifted."""

    def __init__(self, live: Solver, cost: NDArray[np.float64], options: Callable[[Solver], None]) -> None:
        self._solver = Solver()
        self._solver.setOptionValue("output_flag", False)  # noqa: FBT003 (HiGHS option value)
        self._solver.setOptionValue("log_to_console", False)  # noqa: FBT003 (HiGHS option value)
        options(self._solver)
        self._solver.passModel(live.getModel())
        self._basis = live.getBasis()
        self._solver.setBasis(self._basis)
        self._columns = np.arange(self._solver.getNumCol(), dtype=np.int32)
        self._cost = cost

    def restart(self) -> None:
        """Start the next solve from the plan's basis."""
        self._solver.setBasis(self._basis)

    def solve(self, energy: NDArray[np.float64], price: float) -> _Point:
        """Solve with ``price`` added to the price of each kWh of ``energy`` and return the result."""
        costs = self._cost + price * energy
        self._solver.changeColsCost(len(self._columns), self._columns, costs)
        self._solver.run()
        status = self._solver.getModelStatus()
        if status != HighsModelStatus.kOptimal:
            raise SolverError(self._solver.modelStatusToString(status))
        columns = np.asarray(self._solver.getSolution().col_value)
        return _Point(price, float(costs @ columns), float(energy @ columns))


def _kinks(probe: _Probe, energy: NDArray[np.float64], low: _Point, high: _Point, depth: int = 0) -> list[_Point]:
    """Return the kinks strictly between two solves, each as the point where the cost lines on either side cross.

    A kink's energy is the energy just above it.
    """
    if low.energy - high.energy <= _POWER_TOLERANCE * abs(energy).max():
        return []
    crossing = (high.cost - low.cost + low.energy * low.price - high.energy * high.price) / (low.energy - high.energy)
    middle = probe.solve(energy, crossing)
    on_lines = low.cost + low.energy * (crossing - low.price)
    if on_lines - middle.cost <= _COST_TOLERANCE or depth >= _MAX_DEPTH:
        return [_Point(crossing, on_lines, high.energy)]
    return [*_kinks(probe, energy, low, middle, depth + 1), *_kinks(probe, energy, middle, high, depth + 1)]


def offer_curves(
    solver: Solver,
    cost: NDArray[np.float64],
    options: Callable[[Solver], None],
    durations: NDArray[np.float64],
    flow: LinearArray,
    *,
    windows: Sequence[Sequence[int]],
    low: Sequence[float],
    high: Sequence[float],
) -> list[OfferCurve]:
    """Return the offer curve of a flow over each of the given windows.

    Args:
        solver: Solver holding an optimal plan, which is left as it is.
        cost: Cost of each column, the objective the plan minimizes.
        options: Applies the solve options to a solver.
        durations: Duration of each period in hours.
        flow: Power in kW of the flow each period, with one row per period.
            Its price is the price of each kWh of it, so a flow that is an
            import minus an export is priced as both prices moving together.
        windows: Indices of the periods in each window, each window's price
            shifted by the same amount in all of its periods.
        low: Lowest price shift in $/kWh to trace each window from.
        high: Highest price shift in $/kWh to trace each window to.

    """
    probe = _Probe(solver, cost, options)
    curves: list[OfferCurve] = []
    for window, bottom_price, top_price in zip(windows, low, high, strict=True):
        probe.restart()
        periods = np.asarray(window, dtype=np.intp)
        duration = float(durations[periods].sum())
        energy = (flow[periods] * durations[periods]).total().column_coefficients(len(cost))
        bottom = probe.solve(energy, bottom_price)
        top = probe.solve(energy, top_price)
        points = [bottom, *_kinks(probe, energy, bottom, top)]
        steps: list[OfferStep] = []
        for point in points:
            power = point.energy / duration
            if steps and abs(steps[-1].power - power) <= _POWER_TOLERANCE:
                continue
            steps.append(OfferStep(point.price, power))
        curves.append(OfferCurve(tuple(window), tuple(steps)))
    return curves


__all__ = ["OfferCurve", "OfferStep", "offer_curves"]
