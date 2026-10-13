"""Tests for linear expressions and constraint rows."""

import numpy as np
import pytest

from custom_components.haeo.core.model.linear import LinearArray
from custom_components.haeo.core.model.solver import Solver


def _variables(count: int) -> tuple[LinearArray, LinearArray]:
    solver = Solver()
    return solver.add_variables(count), solver.add_variables(count)


def test_linear_array_repr_shows_each_row_as_an_expression() -> None:
    """Rows read as expressions over columns, with unit coefficients and zero constants left out."""
    x, y = _variables(2)

    assert repr(x * 2.0 - y + 1.5) == "LinearArray(2 rows)\n  [0] 2·x0 - x2 + 1.5\n  [1] 2·x1 - x3 + 1.5"
    assert repr(-x[0]) == "LinearArray(1 row)\n  [0] -x0"
    assert repr(LinearArray.constants(np.array([-2.0]))) == "LinearArray(1 row)\n  [0] -2"


def test_rows_repr_shows_bounds() -> None:
    """Each row shows its comparison, with free rows marked."""
    x, y = _variables(1)

    assert repr(x - y * 0.5 <= 0.0) == "Rows(1 row)\n  [0] x0 - 0.5·x1 <= 0"
    assert repr(x >= 1.0) == "Rows(1 row)\n  [0] x0 >= 1"
    assert repr(x + 2.0 == 5.0) == "Rows(1 row)\n  [0] x0 == 3"
    assert repr(x.free()) == "Rows(1 row)\n  [0] x0 (free)"


def test_rows_repr_shows_two_sided_bounds() -> None:
    """A row bounded on both sides shows both bounds."""
    x, _ = _variables(1)
    rows = x <= 4.0
    bounded = type(rows)(rows.expr, np.array([1.0]), rows.upper)

    assert repr(bounded) == "Rows(1 row)\n  [0] 1 <= x0 <= 4"


def test_long_repr_elides_middle_rows() -> None:
    """Long arrays show their first and last rows."""
    x, _ = _variables(8)

    assert repr(x).splitlines() == [
        "LinearArray(8 rows)",
        "  [0] x0",
        "  [1] x1",
        "  [2] x2",
        "  ... 2 more rows",
        "  [5] x5",
        "  [6] x6",
        "  [7] x7",
    ]


def test_single_row_broadcasts_against_per_row_values() -> None:
    """A single row combined with per-row values repeats for each value, as numpy broadcasts."""
    x, y = _variables(3)
    per_row = np.array([1.0, 2.0, 3.0])

    assert repr(x[0] * per_row) == "LinearArray(3 rows)\n  [0] x0\n  [1] 2·x0\n  [2] 3·x0"
    assert repr(x[0] + per_row) == "LinearArray(3 rows)\n  [0] x0 + 1\n  [1] x0 + 2\n  [2] x0 + 3"
    assert repr(x[0] <= per_row) == "Rows(3 rows)\n  [0] x0 <= 1\n  [1] x0 <= 2\n  [2] x0 <= 3"
    assert repr(y - x[0]) == "LinearArray(3 rows)\n  [0] x3 - x0\n  [1] x4 - x0\n  [2] x5 - x0"


def test_mismatched_row_counts_raise() -> None:
    """Arrays of different lengths, neither a single row, cannot be combined."""
    x, _ = _variables(3)

    with pytest.raises(ValueError, match="Cannot combine 2 rows with 3 rows"):
        _ = x[:2] + x
    with pytest.raises(ValueError, match="Cannot combine 3 rows with 2 rows"):
        _ = x * np.array([1.0, 2.0])


def test_numpy_integer_selects_a_single_row() -> None:
    """A numpy integer index selects one row like a Python integer."""
    x, _ = _variables(3)

    assert repr(x[np.int64(1)]) == repr(x[1]) == "LinearArray(1 row)\n  [0] x1"
    assert repr(x[-1]) == "LinearArray(1 row)\n  [0] x2"


def test_sum_of_nothing_raises_a_clear_error() -> None:
    """Summing no arrays names the zeros starting point instead of failing inside numpy."""
    with pytest.raises(ValueError, match=r"LinearArray\.zeros"):
        LinearArray.sum_of([])


def test_rows_compare_by_identity() -> None:
    """Rows hold arrays, so equality is identity rather than an ambiguous elementwise comparison."""
    x, _ = _variables(1)
    rows = x <= 1.0

    assert rows in [rows]
    assert rows != (x <= 1.0)


def test_matrix_product_couples_rows_through_coefficients() -> None:
    """Each row of a matrix product sums the coefficient-weighted rows it reaches, without zero terms."""
    x, _ = _variables(3)
    matrix = np.array([[1.0, 0.0, 0.0], [0.5, 2.0, 0.0]])

    assert repr(matrix @ (x + 1.0)) == "LinearArray(2 rows)\n  [0] x0 + 1\n  [1] 0.5·x0 + 2·x1 + 2.5"


def test_matrix_product_rejects_mismatched_shapes() -> None:
    """A matrix must have one column per row it multiplies."""
    x, _ = _variables(3)

    with pytest.raises(ValueError, match=r"Cannot multiply a \(2, 2\) matrix by 3 rows"):
        _ = np.ones((2, 2)) @ x
