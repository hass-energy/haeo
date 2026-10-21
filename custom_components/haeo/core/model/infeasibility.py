"""Explain and relax a model whose constraints cannot all hold.

When no plan satisfies every constraint, HiGHS can name an irreducible
infeasible subsystem: a smallest set of rows that conflict on their own.
It can also find the smallest weighted violation of the rows that makes the
model feasible, which is how a relaxed plan is found.

Rows are named here by the element and constraint that own them, and the
period they cover, so a conflict reads in terms of the network.
"""

from collections.abc import Iterable, Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Final, NamedTuple

from highspy import Highs, HighsStatus, IisStrategy
import numpy as np
from numpy.typing import NDArray

from .util.solver_rows import RowIndices

# Relaxing a power balance leaves energy unserved or unabsorbed at one point
# in the network, which says plainly what went wrong. Every other row is a
# limit, so it gives way only when no power balance can make the plan feasible.
BALANCE_RELAXATION_WEIGHT: Final = 1.0
LIMIT_RELAXATION_WEIGHT: Final = 1000.0

# A relaxed row is reported when it moves further than this past its bound (kWh).
# Every row the relaxation moves is widened, however little, so the plan stays feasible.
RELAXATION_TOLERANCE: Final = 1e-6

# Rows named in a message before the rest are counted instead
MAX_LISTED_ROWS: Final = 10

# Search the whole LP for a subsystem and reduce it until no row can be dropped
_IIS_STRATEGY: Final = int(IisStrategy.kIisStrategyFromLp) | int(IisStrategy.kIisStrategyIrreducible)


@dataclass(frozen=True, slots=True)
class RowLabel:
    """The element, constraint, and period a solver row belongs to.

    ``balance`` marks a row that balances one tag's power at an element, where a
    shortfall reads as energy no source could supply or nothing could absorb.
    """

    element: str
    constraint: str
    period: int | None
    balance: bool = False

    def __str__(self) -> str:
        """Render the row as ``element constraint[period]``."""
        period = "" if self.period is None else f"[{self.period}]"
        return f"{self.element} {self.constraint}{period}"


@dataclass(frozen=True, slots=True)
class Relaxation:
    """A row a relaxed plan moved past its bound, and by how much.

    The amount is in the row's own units, which are kWh for power balances and
    power limits. It is positive when the row exceeds its upper bound and
    negative when it falls below its lower bound, so a power balance with a
    negative amount drew energy no source could supply.
    """

    row: RowLabel
    amount: float

    def __str__(self) -> str:
        """Render the row and how far past its bound it went."""
        return f"{self.row} by {self.amount:+.3g}"


class InfeasibleError(ValueError):
    """No plan satisfies every constraint."""

    def __init__(self, conflicts: tuple[RowLabel, ...] = ()) -> None:
        """Record the rows that conflict, when they are known."""
        self.conflicts = conflicts
        message = "Optimization failed with status: Infeasible"
        if conflicts:
            message += f" (conflicting constraints: {listing(map(str, conflicts))})"
        super().__init__(message)


def listing(items: Iterable[str]) -> str:
    """Join items with commas, counting those past ``MAX_LISTED_ROWS`` instead of naming them."""
    names = list(items)
    shown = ", ".join(names[:MAX_LISTED_ROWS])
    hidden = len(names) - MAX_LISTED_ROWS
    return f"{shown}, and {hidden} more" if hidden > 0 else shown


def row_labels(
    constraints: Mapping[str, Mapping[str, RowIndices]], n_periods: int, balance_rows: AbstractSet[int]
) -> dict[int, RowLabel]:
    """Label every solver row with the element and constraint that own it.

    A constraint covers the horizon in blocks of one row per period, so a row's
    period is its position within its block. Connection segments name their
    constraints with the connection's name as a prefix, which is dropped.
    """
    labels: dict[int, RowLabel] = {}
    for element, element_constraints in constraints.items():
        for constraint, rows in element_constraints.items():
            name = constraint.removeprefix(f"{element}_")
            whole_blocks = len(rows) % n_periods == 0
            for position, row in enumerate(rows.tolist()):
                period = position % n_periods if whole_blocks else None
                labels[row] = RowLabel(element, name, period, balance=row in balance_rows)
    return labels


def conflicting_rows(solver: Highs, labels: Mapping[int, RowLabel]) -> tuple[RowLabel, ...]:
    """Return a smallest set of rows that cannot all hold, from a solve that found the model infeasible."""
    _, previous = solver.getOptionValue("iis_strategy")
    solver.setOptionValue("iis_strategy", _IIS_STRATEGY)
    try:
        status, iis = solver.getIis()
    finally:
        solver.setOptionValue("iis_strategy", previous)
    if status != HighsStatus.kOk or not iis.valid_:
        return ()
    return tuple(labels[row] for row in iis.row_index_)


class RelaxedRows(NamedTuple):
    """Rows a relaxation moved, the values it moved them to, and their bounds before it."""

    rows: NDArray[np.int32]
    values: NDArray[np.float64]
    lower: NDArray[np.float64]
    upper: NDArray[np.float64]


def relaxed_rows(solver: Highs, labels: Mapping[int, RowLabel]) -> RelaxedRows | None:
    """Return the rows a smallest weighted relaxation moves, the values it moves them to, and their bounds.

    Only rows give way, never variable bounds, and power balances give way
    before limits. Every row the relaxation moves is returned, however little.
    Returns None when no relaxation of the rows is feasible.
    """
    weights = np.full(solver.getNumRow(), LIMIT_RELAXATION_WEIGHT)
    for row, label in labels.items():
        if label.balance:
            weights[row] = BALANCE_RELAXATION_WEIGHT
    not_relaxable = -1.0
    status = solver.feasibilityRelaxation(not_relaxable, not_relaxable, LIMIT_RELAXATION_WEIGHT, None, None, weights)
    solution = solver.getSolution()
    if status != HighsStatus.kOk or not solution.value_valid:
        return None

    lp = solver.getLp()
    values = np.asarray(solution.row_value, dtype=np.float64)
    lower = np.asarray(lp.row_lower_, dtype=np.float64)
    upper = np.asarray(lp.row_upper_, dtype=np.float64)
    rows = np.flatnonzero(np.maximum(values - upper, 0.0) - np.maximum(lower - values, 0.0)).astype(np.int32)
    return RelaxedRows(rows, values[rows], lower[rows], upper[rows])


__all__ = [
    "BALANCE_RELAXATION_WEIGHT",
    "LIMIT_RELAXATION_WEIGHT",
    "MAX_LISTED_ROWS",
    "RELAXATION_TOLERANCE",
    "InfeasibleError",
    "Relaxation",
    "RelaxedRows",
    "RowLabel",
    "conflicting_rows",
    "listing",
    "relaxed_rows",
    "row_labels",
]
