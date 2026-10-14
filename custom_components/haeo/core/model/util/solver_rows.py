"""Add and update blocks of HiGHS constraint rows."""

from dataclasses import dataclass, replace
from typing import Final

from highspy import Highs, HighsStatus
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.linear import Rows

# HiGHS drops matrix coefficients smaller than its small_matrix_value option
# (default 1e-9) and reports a warning, so terms this small are removed before
# rows reach the solver. HiGHS would discard them anyway.
SMALL_MATRIX_VALUE: Final = 1e-9

type RowIndices = NDArray[np.int32]
"""Positions in the solver's matrix of a constraint's rows, in the order the constraint returned them.

A row's index stays fixed for the life of the solver, so it identifies the row's
shadow price in the solution and the row in solver diagnostics.
"""


@dataclass(frozen=True, slots=True)
class AppliedRows:
    """Rows as the solver holds them, in compressed sparse row form.

    Repeated columns within a row are summed and negligible terms removed, with
    each row's entries sorted by column, so two blocks holding the same rows
    have identical arrays.
    """

    lower: NDArray[np.float64]
    upper: NDArray[np.float64]
    starts: NDArray[np.int32]
    row_of: NDArray[np.int64]
    index: NDArray[np.int32]
    values: NDArray[np.float64]

    def __len__(self) -> int:
        """Return the number of rows."""
        return len(self.lower)

    @property
    def is_free(self) -> bool:
        """Return whether every row is unbounded, so the block is in the LP but does not bind."""
        return bool(np.all(np.isneginf(self.lower) & np.isposinf(self.upper)))


def applied_form(rows: Rows) -> AppliedRows:
    """Return the rows with repeated columns summed, negligible terms removed, and entries sorted."""
    n, width = rows.expr.cols.shape
    row_of = np.repeat(np.arange(n, dtype=np.int64), width)
    cols = rows.expr.cols.ravel()
    values = rows.expr.coefs.ravel()

    # Zero terms, such as the padding of shorter rows, add nothing to any sum
    nonzero = values != 0.0
    row_of, cols, values = row_of[nonzero], cols[nonzero], values[nonzero]

    order = np.lexsort((cols, row_of))
    row_of, cols, values = row_of[order], cols[order], values[order]
    if len(cols):
        first = np.ones(len(cols), dtype=bool)
        first[1:] = (row_of[1:] != row_of[:-1]) | (cols[1:] != cols[:-1])
        groups = np.flatnonzero(first)
        values = np.add.reduceat(values, groups)
        row_of, cols = row_of[groups], cols[groups]

    keep = np.abs(values) >= SMALL_MATRIX_VALUE
    row_of, cols, values = row_of[keep], cols[keep], values[keep]
    return AppliedRows(
        lower=np.asarray(rows.lower, dtype=np.float64),
        upper=np.asarray(rows.upper, dtype=np.float64),
        starts=np.searchsorted(row_of, np.arange(n)).astype(np.int32),
        row_of=row_of,
        index=cols.astype(np.int32),
        values=values,
    )


def add_rows(solver: Highs, rows: Rows) -> tuple[RowIndices, AppliedRows]:
    """Add the rows to the solver and return their row indices and applied form.

    HiGHS adds nothing when it rejects a block, so a failed add can be retried.
    """
    applied = applied_form(rows)
    first_row = solver.getNumRow()
    status = solver.addRows(
        len(applied),
        applied.lower,
        applied.upper,
        len(applied.index),
        applied.starts,
        applied.index,
        applied.values,
    )
    if status == HighsStatus.kError:
        msg = f"HiGHS refused to add {len(applied)} constraint rows"
        raise RuntimeError(msg)
    return np.arange(first_row, first_row + len(applied), dtype=np.int32), applied


def change_bounds(
    solver: Highs,
    indices: RowIndices,
    applied: AppliedRows,
    lower: float,
    upper: float,
) -> AppliedRows:
    """Give every row the bounds ``lower`` and ``upper``, leaving its coefficients alone."""
    count = len(applied)
    new_lower, new_upper = np.full(count, lower), np.full(count, upper)
    solver.changeRowsBounds(count, indices, new_lower, new_upper)
    return replace(applied, lower=new_lower, upper=new_upper)


def update_rows(solver: Highs, indices: RowIndices, applied: AppliedRows, rows: Rows) -> AppliedRows:
    """Change rows from the applied form they hold to ``rows``, returning the new applied form.

    The rows are diffed against what was last written rather than read back from
    the solver. HiGHS stores its matrix column-wise, so reading a row scans the
    whole matrix, and every changeCoeff call discards the simplex factorization,
    so only values that differ are written.
    """
    new = applied_form(rows)

    bounds_changed = np.flatnonzero((new.lower != applied.lower) | (new.upper != applied.upper))
    if len(bounds_changed):
        solver.changeRowsBounds(
            len(bounds_changed),
            indices[bounds_changed],
            new.lower[bounds_changed],
            new.upper[bounds_changed],
        )

    if (
        np.array_equal(new.row_of, applied.row_of)
        and np.array_equal(new.index, applied.index)
        and np.array_equal(new.values, applied.values)
    ):
        return new

    width = int(max(np.max(new.index, initial=0), np.max(applied.index, initial=0))) + 1
    old_keys = applied.row_of * width + applied.index
    new_keys = new.row_of * width + new.index
    _, old_pos, new_pos = np.intersect1d(old_keys, new_keys, assume_unique=True, return_indices=True)
    changed = new_pos[applied.values[old_pos] != new.values[new_pos]]
    added = np.flatnonzero(~np.isin(new_keys, old_keys, assume_unique=True))
    removed = np.flatnonzero(~np.isin(old_keys, new_keys, assume_unique=True))

    for pos in np.concatenate([changed, added]):
        solver.changeCoeff(int(indices[new.row_of[pos]]), int(new.index[pos]), float(new.values[pos]))
    for pos in removed:
        solver.changeCoeff(int(indices[applied.row_of[pos]]), int(applied.index[pos]), 0.0)
    return new


__all__ = [
    "SMALL_MATRIX_VALUE",
    "AppliedRows",
    "RowIndices",
    "add_rows",
    "applied_form",
    "change_bounds",
    "update_rows",
]
