"""Recommended hardware limits for the first period of a solved plan.

The plan says how much power each connection carries, but not which of those
flows the hardware must be stopped from exceeding. Left alone, hardware running
self-consumption pushes some flows on its own: generation runs up to what is
available, and storage absorbs surplus and covers shortfalls. Where one of those
pushes would cost the plan money, a limit is needed, and it belongs on the flow
the cost lands on, not necessarily the one being pushed. More solar that could
only go out through a negative-priced export is stopped by limiting export, so
the solar is still free to cover a load that turns out larger than forecast.

Each connection power limit the hardware can be set to is a control point; limits
that only model something, such as an EV being away driving, are left out. Each driven point
(generation, or storage, which never trades with the grid or curtails generation
under self-consumption) is pushed as far as it will go on a copy of the solved
model, warm-started from the plan's basis, so the plan and its solver are never
touched. When the push costs money, the cost is split by the elements whose cost
terms it changed. A first-period point that rose with the push and carries that
cost is limited; otherwise the pushed point itself is. Pushes repeat with the
limits in place until none costs anything, and any limit the others make
unnecessary is dropped.

Reading the same split from the plan's simplex tableau alone is not enough: the
plan's LP is primal degenerate, so the first pivot of a real move often goes
nowhere, and a free move at the margin can turn costly further on.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import IntEnum
import math
from typing import (
    TYPE_CHECKING,
    Any,  # noqa: TID251  # the network's elements and connections are invariant in their output-name
    # Literal, so a mapping of mixed concrete elements has no common type but Element[Any]
    Final,
)

from highspy import Highs, HighsModelStatus
import numpy as np
from numpy.typing import NDArray

from .element import NetworkElement
from .elements.connection import Connection
from .elements.segments.power_limit import PowerLimitSegment

if TYPE_CHECKING:
    from .element import Element
    from .solver import Solver

# Push costs at or below this are free, in $/kWh
COST_TOLERANCE: Final = 1e-6

# The shortest push worth probing, in kWh; anything that can move less is at its limit
PUSH: Final = 1e-3

# Halvings spent finding how far a point can go when its full headroom is out of reach
BISECTIONS: Final = 3

# The furthest a probe pushes a point without a max power, in kWh
FULL_PUSH: Final = 1e3

# Headroom below this, in kWh, leaves a point at its limit
STEP_TOLERANCE: Final = 1e-9


class Role(IntEnum):
    """What a control point connects to, in self-consumption priority order."""

    OWN = 0
    """Generation into the system or consumption out of it, which runs first."""

    STORAGE = 1
    """Storage that the system charges and discharges."""

    EXTERNAL = 2
    """An external connection such as the grid, the last resort."""

    PASS_THROUGH = 3
    """A connection between two junctions, which carries whatever its ends need."""


@dataclass(frozen=True, slots=True)
class ControlPoint:
    """A connection's power limit in the first period."""

    name: str
    ends: tuple[str, str]
    """The connection's source and target element names."""
    row: int
    is_source: bool
    """Whether the point supplies the network (its far end is its source)."""
    role: Role
    period: float


@dataclass(frozen=True, slots=True)
class LimitRecommendation:
    """What to apply to a control point's hardware limit now."""

    power: float
    """The planned power (kW)."""

    max_power: float | None
    """The limit to apply (kW), or None when the hardware can run unrestricted."""

    push_cost: float
    """What each kWh the limit stops would cost the plan ($/kWh), 0 when unrestricted."""


def _is_junction(element: "Element[Any]") -> bool:
    return isinstance(element, NetworkElement) and not element.is_source and not element.is_sink


def _role(connection: Connection[Any], terminal: "Element[Any]") -> Role:
    if connection.is_external:
        return Role.EXTERNAL
    if isinstance(terminal, NetworkElement) and terminal.is_source and terminal.is_sink:
        return Role.STORAGE
    return Role.OWN


def control_points(
    connections: Iterable[Connection[Any]], elements: Mapping[str, "Element[Any]"], period: float
) -> list[ControlPoint]:
    """Return the first-period power limit of every connection that has one the plan can choose under."""
    points: list[ControlPoint] = []
    for connection in connections:
        limits = [
            s
            for s in connection.segments.values()
            if isinstance(s, PowerLimitSegment) and s.control_point and not s.fixed
        ]
        if not limits:
            continue
        source, target = elements[connection.source], elements[connection.target]
        if _is_junction(source) and _is_junction(target):
            is_source, role = False, Role.PASS_THROUGH
        elif _is_junction(source):
            is_source, role = False, _role(connection, target)
        else:
            is_source, role = True, _role(connection, source)
        row = int(limits[0].constraints()["power_limit"][0])
        points.append(
            ControlPoint(connection.name, (connection.source, connection.target), row, is_source, role, period)
        )
    return points


def _is_driven(point: ControlPoint) -> bool:
    """Return whether the hardware pushes the point on its own: generation and storage."""
    return point.role == Role.STORAGE or (point.is_source and point.role == Role.OWN)


def _probe(solver: "Solver") -> Highs:
    """Return a separate solver holding the plan's model and basis, so probing never moves the plan."""
    probe = Highs()
    output_off = False
    probe.setOptionValue("output_flag", output_off)
    probe.passModel(solver.getModel())
    probe.setOptionValue("solver", "simplex")
    probe.setOptionValue("simplex_strategy", 1)
    probe.setBasis(solver.getBasis())
    return probe


def _owner(column_name: str, names: list[str]) -> str | None:
    """Return the element a column belongs to, from the ``element.quantity`` names the solver gives its columns."""
    owners = [name for name in names if column_name.startswith(f"{name}.")]
    return max(owners, key=len) if owners else None


class _Prober:
    """Pushes first-period flows on a copy of the plan and finds where the extra cost lands."""

    def __init__(self, solver: "Solver", points: list[ControlPoint], element_names: list[str]) -> None:
        self.solver = solver
        self.points = points
        self.element_names = element_names
        self.rows = np.array([point.row for point in points], dtype=np.int32)
        _, _, self.lower, self.upper, _ = solver.getRows(len(self.rows), self.rows)
        self.activity = solver.row_values()[self.rows]
        self.plan = solver.column_values()
        self.plan_cost = solver.getObjectiveValue()
        self.cost = np.asarray(solver.getLp().col_cost_)
        self.probe = _probe(solver)
        self.basis = self.probe.getBasis()
        index_of = {point.ends: i for i, point in enumerate(points)}
        # Each point's reverse connection, when that is a point too
        self.reverse = [index_of.get((point.ends[1], point.ends[0])) for point in points]
        active_ends = {point.ends for point, flow in zip(points, self.activity, strict=True) if flow > STEP_TOLERANCE}
        self.reverse_active = np.array([(point.ends[1], point.ends[0]) in active_ends for point in points])

    def headroom(self, index: int) -> float:
        return float(self.upper[index] - self.activity[index])

    def push(self, index: int, step: float, capped: set[int]) -> NDArray[np.float64] | None:
        """Return the plan's columns with ``step`` more energy through a point, or None when it cannot rise.

        No hardware runs a connection and its reverse at once, and losses around
        such a loop would absorb any energy, so when a push runs both, the leg the
        plan leaves idle is held idle and the push is solved again.
        """
        pushed = self.points[index]
        upper = self.upper.copy()
        lower = self.lower.copy()
        # Self-consumption never trades storage with external connections, nor curtails generation for it
        if pushed.role == Role.STORAGE:
            external = np.array([point.role == Role.EXTERNAL for point in self.points])
            generation = np.array([point.is_source and point.role == Role.OWN for point in self.points])
            upper = np.where(external, np.minimum(upper, self.activity), upper)
            lower = np.where(generation, self.activity, lower)
        for i in capped:
            upper[i] = self.activity[i]
        lower[index], upper[index] = self.activity[index] + step, self.upper[index]
        while True:
            self.probe.changeRowsBounds(len(self.rows), self.rows, lower, upper)
            self.probe.setBasis(self.basis)
            self.probe.run()
            if self.probe.getModelStatus() != HighsModelStatus.kOptimal:
                return None
            flow = np.asarray(self.probe.getSolution().row_value)[self.rows]
            loops = [
                (i, j)
                for i, j in enumerate(self.reverse)
                if j is not None
                and i < j
                and min(flow[i], flow[j]) > STEP_TOLERANCE
                and min(self.activity[i], self.activity[j]) <= STEP_TOLERANCE
            ]
            if not loops:
                return np.asarray(self.probe.getSolution().col_value)
            for i, j in loops:
                # Hold the leg the plan leaves idle; the pushed point is never the idle leg of an active pair
                upper[i if self.activity[i] <= STEP_TOLERANCE and i != index else j] = 0.0

    def blame(self, index: int, columns: NDArray[np.float64]) -> int:
        """Return the point whose extra cost the push lands on: a first-period point that rose with it, or itself.

        Cost on an element other than a connection, such as a battery's charge
        penalty, is blamed on the risen points into or out of that element.
        """
        change = columns - self.plan
        rows = self.probe.getSolution().row_value
        risen = {
            point.name: i
            for i, point in enumerate(self.points)
            if i != index and rows[point.row] > self.activity[i] + STEP_TOLERANCE
        }
        shares: dict[int, float] = {}
        for column in np.flatnonzero(np.abs(self.cost * change) > COST_TOLERANCE * STEP_TOLERANCE):
            owner = _owner(self.solver.column_name(int(column)), self.element_names)
            # A connection's own cost is its own; an element's is shared by the risen points at its ends
            blamed = [risen[owner]] if owner in risen else [i for i in risen.values() if owner in self.points[i].ends]
            for i in blamed:
                shares[i] = shares.get(i, 0.0) + float(self.cost[column] * change[column])
        culprit = max(shares, key=lambda i: shares[i], default=None)
        return index if culprit is None or shares[culprit] <= 0.0 else culprit


def _driven(prober: _Prober) -> list[int]:
    """Return the driven points that could carry more than planned."""
    return [
        i
        for i, point in enumerate(prober.points)
        if _is_driven(point) and not prober.reverse_active[i] and prober.headroom(i) > STEP_TOLERANCE
    ]


@dataclass(frozen=True, slots=True)
class _Push:
    """What pushing a point taught: infinite cost when it cannot rise, and the columns when it costs money."""

    cost: float
    columns: NDArray[np.float64] | None = None


def _push(prober: _Prober, index: int, capped: set[int]) -> _Push:
    """Push a point and return what each extra kWh costs.

    The shortest push settles a point that cannot rise or that costs money at
    once. One that is free at the margin is pushed to its headroom, or as far
    short of it as bisection finds feasible, so a free band does not hide the
    cost of going further.
    """
    columns = prober.push(index, PUSH, capped)
    if columns is None:
        return _Push(math.inf)
    cost = (prober.probe.getObjectiveValue() - prober.plan_cost) / PUSH
    if cost > COST_TOLERANCE:
        return _Push(cost, columns)
    feasible, infeasible = PUSH, min(prober.headroom(index), FULL_PUSH)
    further = prober.push(index, infeasible, capped)
    if further is not None:
        feasible, columns = infeasible, further
    else:
        for _ in range(BISECTIONS):
            middle = (feasible + infeasible) / 2
            if (further := prober.push(index, middle, capped)) is None:
                infeasible = middle
            else:
                feasible, columns = middle, further
    if feasible <= PUSH:
        return _Push(0.0)
    # Bisection leaves the probe at its last push, which may not be the furthest feasible one
    prober.push(index, feasible, capped)
    cost = (prober.probe.getObjectiveValue() - prober.plan_cost) / feasible
    return _Push(cost, columns) if cost > COST_TOLERANCE else _Push(0.0)


def recommend_limits(
    solver: "Solver",
    connections: Iterable[Connection[Any]],
    elements: Mapping[str, "Element[Any]"],
    period: float,
) -> dict[str, LimitRecommendation]:
    """Return the recommended first-period limit of each control point, by connection name."""
    points = control_points(connections, elements, period)
    prober = _Prober(solver, points, list(elements))
    capped: dict[int, float] = {}
    # A point that cannot rise stays that way as caps are added, so it is pushed once
    blocked: set[int] = set()
    changed = True
    while changed:
        changed = False
        for i in _driven(prober):
            if i in capped or i in blocked:
                continue
            pushed = _push(prober, i, set(capped))
            if pushed.cost == math.inf:
                blocked.add(i)
            elif pushed.columns is not None:
                capped[prober.blame(i, pushed.columns)] = pushed.cost
                changed = True
    # Drop any cap the others already make unnecessary, latest first; a lone cap is needed by construction
    if len(capped) > 1:
        for i in sorted(capped, reverse=True):
            others = set(capped) - {i}
            # Points blocked under every cap may rise once one is lifted, so each is pushed again
            if all(j in others or _push(prober, j, others).columns is None for j in _driven(prober)):
                del capped[i]
    recommendations: dict[str, LimitRecommendation] = {}
    for i, point in enumerate(points):
        # The limit rows are energy, so their activity over the period is the power
        power = float(prober.activity[i]) / point.period
        recommendations[point.name] = LimitRecommendation(
            power=power,
            max_power=max(power, 0.0) if i in capped else None,
            push_cost=capped.get(i, 0.0),
        )
    return recommendations
