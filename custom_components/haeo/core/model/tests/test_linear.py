"""Tests for the readable representation of linear expressions and rows."""

import numpy as np

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
