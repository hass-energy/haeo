"""Array-native linear expressions and constraint rows for the LP model.

A ``LinearArray`` holds one linear expression per row over the solver's columns.
Every row has the same number of terms, so the expressions are stored as a
column index matrix and a coefficient matrix of shape ``(rows, terms)`` plus a
constant per row. Arithmetic on whole arrays is then a handful of numpy
operations, independent of the number of periods.

Comparing a ``LinearArray`` with values produces ``Rows``: the expressions with
the constants moved into lower and upper row bounds, ready to add to the solver.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import ClassVar, Final, Self, overload

import numpy as np
from numpy.typing import NDArray

INF: Final = float("inf")

type Values = float | NDArray[np.float64]
"""A scalar, or one value per row."""

type ColumnNamer = Callable[[int], str]
"""Gives the display name of a solver column."""


# Rows shown at each end of a long array's repr
_REPR_EDGE_ROWS: Final = 3


def _format_number(value: float) -> str:
    """Format a coefficient or bound compactly, showing negative zero as zero."""
    return f"{value + 0.0:g}"


def index_name(column: int) -> str:
    """Name a column by its solver index, as ``x5``."""
    return f"x{column}"


def _format_terms(
    cols: NDArray[np.int64],
    coefs: NDArray[np.float64],
    constant: float,
    column_name: ColumnNamer,
) -> str:
    """Format one row's terms as ``2·x5 - x7 + 1.5``, omitting zero terms."""
    terms = [(col, coef) for col, coef in zip(cols.tolist(), coefs.tolist(), strict=True) if coef != 0.0]
    parts = [
        f"{'-' if coef < 0 else '+'} {'' if abs(coef) == 1.0 else f'{_format_number(abs(coef))}·'}{column_name(col)}"
        for col, coef in terms
    ]
    if constant != 0.0 or not parts:
        parts.append(f"{'-' if constant < 0 else '+'} {_format_number(abs(constant))}")
    text = " ".join(parts)
    return text[2:] if text.startswith("+ ") else "-" + text[2:]


def _format_rows(name: str, lines: list[str]) -> str:
    """Format numbered rows, eliding the middle of long arrays."""
    numbered = [f"  [{i}] {line}" for i, line in enumerate(lines)]
    if len(numbered) > 2 * _REPR_EDGE_ROWS:
        hidden = len(numbered) - 2 * _REPR_EDGE_ROWS
        numbered = [*numbered[:_REPR_EDGE_ROWS], f"  ... {hidden} more rows", *numbered[-_REPR_EDGE_ROWS:]]
    count = f"{len(lines)} row" if len(lines) == 1 else f"{len(lines)} rows"
    return "\n".join([f"{name}({count})", *numbered])


@dataclass(frozen=True, slots=True, eq=False)
class LinearArray:
    """One linear expression per row: ``sum(coefs[i, j] * x[cols[i, j]]) + constant[i]``."""

    cols: NDArray[np.int64]
    coefs: NDArray[np.float64]
    constant: NDArray[np.float64]

    # numpy scalars and arrays defer to this class's reflected operators
    __array_ufunc__ = None

    @classmethod
    def columns(cls, start: int, count: int) -> Self:
        """Return one row per column for ``count`` consecutive columns from ``start``."""
        return cls(
            cols=np.arange(start, start + count, dtype=np.int64)[:, None],
            coefs=np.ones((count, 1)),
            constant=np.zeros(count),
        )

    @classmethod
    def constants(cls, values: Values) -> Self:
        """Return rows with no terms, holding only the given constants."""
        constant = np.asarray(values, dtype=np.float64).reshape(-1)
        return cls(
            cols=np.zeros((len(constant), 0), dtype=np.int64),
            coefs=np.zeros((len(constant), 0)),
            constant=constant,
        )

    @classmethod
    def zeros(cls, count: int) -> Self:
        """Return ``count`` rows that are all zero, the starting point of a sum that may have no terms."""
        return cls.constants(np.zeros(count))

    @classmethod
    def sum_of(cls, items: Iterable[LinearArray]) -> Self:
        """Return the row-wise sum of arrays with the same number of rows."""
        items = list(items)
        if not items:
            msg = "sum_of needs at least one array; start from LinearArray.zeros(count) when there may be none"
            raise ValueError(msg)
        return cls(
            cols=np.concatenate([item.cols for item in items], axis=1),
            coefs=np.concatenate([item.coefs for item in items], axis=1),
            constant=np.sum([item.constant for item in items], axis=0),
        )

    def __len__(self) -> int:
        """Return the number of rows."""
        return len(self.constant)

    def __repr__(self) -> str:
        """Show each row as an expression over columns ``x<index>``, eliding the middle of long arrays."""
        return self.format(index_name)

    def format(self, column_name: ColumnNamer) -> str:
        """Show each row as an expression over named columns, eliding the middle of long arrays."""
        lines = [
            _format_terms(cols, coefs, constant, column_name)
            for cols, coefs, constant in zip(self.cols, self.coefs, self.constant.tolist(), strict=True)
        ]
        return _format_rows("LinearArray", lines)

    def __getitem__(self, key: int | np.integer | slice | NDArray[np.integer]) -> Self:
        """Return the selected rows.

        An integer selects a single row, kept as an array of one. An integer array
        selects its rows in order, repeating any that appear more than once.
        """
        rows = key if isinstance(key, slice | np.ndarray) else slice(int(key), int(key) + 1 or None)
        return type(self)(cols=self.cols[rows], coefs=self.coefs[rows], constant=self.constant[rows])

    def _with_rows(self, count: int) -> Self:
        """Return this array repeated to ``count`` rows when it has one row, as numpy broadcasts."""
        if len(self) == count or count == 1:
            return self
        if len(self) != 1:
            msg = f"Cannot combine {len(self)} rows with {count} rows"
            raise ValueError(msg)
        width = self.cols.shape[1]
        return type(self)(
            cols=np.broadcast_to(self.cols, (count, width)),
            coefs=np.broadcast_to(self.coefs, (count, width)),
            constant=np.broadcast_to(self.constant, (count,)),
        )

    def _with_rows_of(self, values: NDArray[np.float64]) -> Self:
        """Return this array matched to the number of rows of per-row values."""
        return self._with_rows(len(values)) if values.ndim else self

    def __neg__(self) -> Self:
        """Return the negated expressions."""
        return type(self)(cols=self.cols, coefs=-self.coefs, constant=-self.constant)

    def __add__(self, other: LinearArray | Values) -> Self:
        """Add expressions row by row, or add values to the constants."""
        if isinstance(other, LinearArray):
            left, right = self._with_rows(len(other)), other._with_rows(len(self))
            return type(self)(
                cols=np.concatenate([left.cols, right.cols], axis=1),
                coefs=np.concatenate([left.coefs, right.coefs], axis=1),
                constant=left.constant + right.constant,
            )
        values = np.asarray(other, dtype=np.float64)
        rows = self._with_rows_of(values)
        return type(self)(cols=rows.cols, coefs=rows.coefs, constant=rows.constant + values)

    def __radd__(self, other: Values) -> Self:
        """Add values to the constants."""
        return self + other

    def __sub__(self, other: LinearArray | Values) -> Self:
        """Subtract expressions row by row, or subtract values from the constants."""
        if isinstance(other, LinearArray):
            return self + (-other)
        return self + -np.asarray(other, dtype=np.float64)

    def __rsub__(self, other: Values) -> Self:
        """Subtract the expressions from values."""
        return -self + other

    def __mul__(self, scale: Values) -> Self:
        """Scale each row by a scalar or by one value per row."""
        factor = np.asarray(scale, dtype=np.float64)
        rows = self._with_rows_of(factor)
        return type(self)(
            cols=rows.cols,
            coefs=rows.coefs * (factor[:, None] if factor.ndim else factor),
            constant=rows.constant * factor,
        )

    def __rmul__(self, scale: Values) -> Self:
        """Scale each row by a scalar or by one value per row."""
        return self * scale

    def __rmatmul__(self, matrix: NDArray[np.float64]) -> Self:
        """Return ``matrix @ self``: row ``i`` is the sum over ``j`` of ``matrix[i, j]`` times row ``j``.

        Use it when each row couples many rows of another array through a
        coefficient matrix, such as a profile whose energy lands in every period
        a run overlaps. Zero entries add no terms to the LP.
        """
        n_rows, width = self.cols.shape
        if matrix.shape[1:] != (n_rows,):
            msg = f"Cannot multiply a {matrix.shape} matrix by {n_rows} rows"
            raise ValueError(msg)
        n_out = matrix.shape[0]
        return type(self)(
            cols=np.broadcast_to(self.cols.reshape(1, n_rows * width), (n_out, n_rows * width)),
            coefs=(matrix[:, :, None] * self.coefs[None, :, :]).reshape(n_out, n_rows * width),
            constant=matrix @ self.constant,
        )

    def total(self) -> Self:
        """Return a single row holding the sum of all rows."""
        return type(self)(
            cols=self.cols.reshape(1, -1),
            coefs=self.coefs.reshape(1, -1),
            constant=np.array([self.constant.sum()]),
        )

    def column_coefficients(self, n_columns: int) -> NDArray[np.float64]:
        """Return each column's coefficient summed over every term of every row."""
        weighted = np.bincount(self.cols.ravel(), weights=self.coefs.ravel(), minlength=n_columns)
        return weighted.astype(np.float64, copy=False)

    def value(self, column_values: NDArray[np.float64]) -> NDArray[np.float64]:
        """Evaluate each row at the given column values."""
        return (self.coefs * column_values[self.cols]).sum(axis=1) + self.constant

    def __le__(self, other: LinearArray | Values) -> Rows:
        """Return rows bounding each expression above."""
        expr = self - other
        return Rows(expr.without_constant(), np.full(len(expr), -INF), -expr.constant)

    def __ge__(self, other: LinearArray | Values) -> Rows:
        """Return rows bounding each expression below."""
        expr = self - other
        return Rows(expr.without_constant(), -expr.constant, np.full(len(expr), INF))

    def __eq__(self, other: LinearArray | Values) -> Rows:  # type: ignore[override]  # == builds rows, see __hash__
        """Return rows fixing each expression."""
        expr = self - other
        return Rows(expr.without_constant(), -expr.constant, -expr.constant)

    # == builds rows rather than testing equality, so arrays cannot be hashed. Both
    # depart from object's contract on purpose, which is what lets rows read as maths.
    __hash__: ClassVar[None] = None  # pyright: ignore[reportIncompatibleMethodOverride]

    def free(self) -> Rows:
        """Return rows without bounds, which stay in the LP but do not bind."""
        return Rows(self.without_constant(), np.full(len(self), -INF), np.full(len(self), INF))

    def without_constant(self) -> Self:
        """Return the expressions with their constants dropped."""
        return type(self)(cols=self.cols, coefs=self.coefs, constant=np.zeros(len(self)))


@dataclass(frozen=True, slots=True, eq=False)
class Rows:
    """Constraint rows: ``lower <= expr <= upper`` for each row of ``expr``."""

    expr: LinearArray
    lower: NDArray[np.float64]
    upper: NDArray[np.float64]

    @staticmethod
    def concat(blocks: Iterable[Rows]) -> Rows:
        """Stack row blocks, padding shorter rows with zero terms."""
        blocks = list(blocks)
        if not blocks:
            return LinearArray.constants(np.zeros(0)).free()
        width = max(block.expr.cols.shape[1] for block in blocks)

        def padded[T: np.generic](values: NDArray[T]) -> NDArray[T]:
            return np.pad(values, ((0, 0), (0, width - values.shape[1])))

        return Rows(
            expr=LinearArray(
                cols=np.concatenate([padded(block.expr.cols) for block in blocks]),
                coefs=np.concatenate([padded(block.expr.coefs) for block in blocks]),
                constant=np.concatenate([block.expr.constant for block in blocks]),
            ),
            lower=np.concatenate([block.lower for block in blocks]),
            upper=np.concatenate([block.upper for block in blocks]),
        )

    def __len__(self) -> int:
        """Return the number of rows."""
        return len(self.lower)

    def __repr__(self) -> str:
        """Show each row with its bounds over columns ``x<index>``, eliding the middle of long blocks."""
        return self.format(index_name)

    def format(self, column_name: ColumnNamer) -> str:
        """Show each row with its bounds over named columns, eliding the middle of long blocks."""
        lines: list[str] = []
        for cols, coefs, lower, upper in zip(
            self.expr.cols, self.expr.coefs, self.lower.tolist(), self.upper.tolist(), strict=True
        ):
            terms = _format_terms(cols, coefs, 0.0, column_name)
            if lower == upper:
                lines.append(f"{terms} == {_format_number(upper)}")
            elif lower == -INF and upper == INF:
                lines.append(f"{terms} (free)")
            elif lower == -INF:
                lines.append(f"{terms} <= {_format_number(upper)}")
            elif upper == INF:
                lines.append(f"{terms} >= {_format_number(lower)}")
            else:
                lines.append(f"{_format_number(lower)} <= {terms} <= {_format_number(upper)}")
        return _format_rows("Rows", lines)


@overload
def total(items: Iterable[LinearArray]) -> LinearArray: ...


@overload
def total(items: Iterable[LinearArray | None]) -> LinearArray | None: ...


def total(items: Iterable[LinearArray | None]) -> LinearArray | None:
    """Return a single row summing every row of every array, or None when there are none."""
    present = [item.total() for item in items if item is not None]
    if not present:
        return None
    return LinearArray.sum_of(present)


__all__ = ["INF", "LinearArray", "Rows", "total"]
