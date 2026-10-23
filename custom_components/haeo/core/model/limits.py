"""Recommended hardware limits for the first period of a solved plan.

The plan says how much power each connection carries, but not which of those
flows the hardware must be stopped from exceeding. A flow is held back either by
something else (a full battery, a capped export, nothing left to supply) or by
the plan itself, which would pay more if the flow rose. Only the second needs a
limit on the hardware; the first happens on its own.

Each connection with a power limit is a control point. Its push cost is what one
more kWh through it costs the plan. It is found by forcing a little more energy
through the point on a copy of the solved model, warm-started from the plan's
basis, so the plan and its solver are never touched. Reading it from the plan's
simplex tableau alone is not enough: the plan's LP is primal degenerate, so the
first pivot of a real move often goes nowhere and only further pivots price it.

The other control points may only move the way the hardware would move them
under a priority order, self-consumption unless another is given:

- generation (a connection from a source-only element) runs up to its available power;
- connections between two junctions, such as an inverter, carry whatever their ends need;
- a point displaces a point of the same kind (a source or a sink) only when the
  priority ranks it ahead of that point;
- no other storage or external point rises, because each carries its own limit;
- a connection idle in the plan stays idle while its reverse carries power, since
  no hardware runs both directions at once and losses around the loop would
  otherwise absorb any amount of energy.

A point whose push cost is positive is limited to its planned power. One that
can rise for free, or cannot rise at all, is unrestricted. So is one whose
reverse connection carries power in the plan: more through it would first mean
less through the reverse, which a floor on the reverse decides, not a cap here.
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

from .element import NetworkElement
from .elements.connection import Connection
from .elements.segments.power_limit import PowerLimitSegment

if TYPE_CHECKING:
    from .element import Element
    from .solver import Solver

# Push costs at or below this are free, in $/kWh
COST_TOLERANCE: Final = 1e-6

# How far each probe pushes a point past its plan, in kWh over the first period
PUSH: Final = 1e-3

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
class Priority:
    """The order in which the hardware draws on sources and serves sinks, first to last."""

    sources: tuple[Role, ...]
    sinks: tuple[Role, ...]

    def rank(self, point: "ControlPoint") -> int:
        """Return where a point stands among its kind, lower first."""
        return (self.sources if point.is_source else self.sinks).index(point.role)


SELF_CONSUMPTION: Final = Priority(
    sources=(Role.OWN, Role.STORAGE, Role.EXTERNAL),
    sinks=(Role.OWN, Role.STORAGE, Role.EXTERNAL),
)


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
    """What one more kWh through the point costs the plan ($/kWh), infinite when it cannot rise."""


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
        limits = [s for s in connection.segments.values() if isinstance(s, PowerLimitSegment) and not s.fixed]
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


def _may_rise(point: ControlPoint) -> bool:
    return point.role == Role.PASS_THROUGH or (point.is_source and point.role == Role.OWN)


def _may_fall(point: ControlPoint, pushed: ControlPoint, priority: Priority) -> bool:
    if point.role == Role.PASS_THROUGH:
        return True
    if point.is_source and point.role == Role.OWN:
        return False
    if pushed.role == Role.PASS_THROUGH:
        return point.role == Role.EXTERNAL
    return point.is_source == pushed.is_source and priority.rank(pushed) < priority.rank(point)


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


def recommend_limits(
    solver: "Solver",
    connections: Iterable[Connection[Any]],
    elements: Mapping[str, "Element[Any]"],
    period: float,
    priority: Priority = SELF_CONSUMPTION,
) -> dict[str, LimitRecommendation]:
    """Return the recommended first-period limit of each control point under a priority, by connection name."""
    points = control_points(connections, elements, period)
    rows = np.array([point.row for point in points], dtype=np.int32)
    _, _, lower, upper, _ = solver.getRows(len(rows), rows)
    activity = solver.row_values()[rows]
    plan_cost = solver.getObjectiveValue()
    probe = _probe(solver)
    basis = probe.getBasis()
    # Points idle in the plan whose reverse connection is also a point
    reversed_ends = {(point.ends[1], point.ends[0]) for point in points}
    idle_pair = np.array([point.ends in reversed_ends for point in points]) & (activity <= STEP_TOLERANCE)
    active_ends = {point.ends for point, flow in zip(points, activity, strict=True) if flow > STEP_TOLERANCE}
    recommendations: dict[str, LimitRecommendation] = {}
    for i, point in enumerate(points):
        # The limit rows are energy, so their activity over the period is the power
        power = activity[i] / point.period
        step = min(PUSH, upper[i] - activity[i])
        if step <= STEP_TOLERANCE or (point.ends[1], point.ends[0]) in active_ends:
            cost = math.inf
        else:
            # Hold the other points where the hardware's default behavior keeps them
            probe_lower = np.where([_may_fall(p, point, priority) for p in points], lower, activity)
            probe_upper = np.where([_may_rise(p) for p in points] & ~idle_pair, upper, activity)
            probe_lower[i], probe_upper[i] = activity[i] + step, upper[i]
            probe.changeRowsBounds(len(rows), rows, probe_lower, probe_upper)
            probe.setBasis(basis)
            probe.run()
            if probe.getModelStatus() == HighsModelStatus.kOptimal:
                cost = max((probe.getObjectiveValue() - plan_cost) / step, 0.0)
            else:
                cost = math.inf
        limited = COST_TOLERANCE < cost < math.inf
        recommendations[point.name] = LimitRecommendation(
            power=power,
            max_power=max(power, 0.0) if limited else None,
            push_cost=cost,
        )
    return recommendations
