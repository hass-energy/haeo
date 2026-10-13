"""Tests for the solver row helpers."""

from unittest.mock import MagicMock, call

import numpy as np
import pytest

from custom_components.haeo.core.model.linear import INF, LinearArray, Rows
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util.solver_rows import add_rows, applied_form, change_bounds, update_rows


@pytest.fixture
def solver() -> Solver:
    """Return a quiet solver."""
    h = Solver()
    h.setOptionValue("output_flag", False)
    return h


def _row(solver: Solver, row: int) -> tuple[float, float, dict[int, float]]:
    """Return a row's bounds and coefficients as the solver holds them."""
    _, lower, upper, _ = solver.getRow(row)
    _, index, values = solver.getRowEntries(row)
    return lower, upper, {int(i): float(v) for i, v in zip(index, values, strict=True)}


def _terms(cols: list[list[int]], coefs: list[list[float]]) -> LinearArray:
    """Return expressions with the given terms and no constants."""
    return LinearArray(np.array(cols, dtype=np.int64), np.array(coefs), np.zeros(len(cols)))


def test_applied_form_sums_repeated_columns_and_drops_negligible_terms() -> None:
    """Repeated columns are summed, negligible terms removed, and entries sorted by column."""
    applied = applied_form(_terms([[2, 0, 0, 1]], [[4.0, 1.0, 2.0, 3e-10]]) <= 3.0)

    assert applied.index.tolist() == [0, 2]
    assert applied.values.tolist() == [3.0, 4.0]
    assert applied.starts.tolist() == [0]
    assert applied.upper.tolist() == [3.0]


def test_add_rows_writes_bounds_and_coefficients(solver: Solver) -> None:
    """Each row reaches the solver with its bounds, summed coefficients and no negligible terms."""
    x = solver.add_variables(3)

    indices, _ = add_rows(solver, Rows.concat([x[0] + x[0] * 2.0 + x[1] * 3e-10 <= 5.0, x[2] - x[1] >= 1.0]))

    assert indices.tolist() == [0, 1]
    assert _row(solver, 0) == (-INF, 5.0, {0: 3.0})
    assert _row(solver, 1) == (1.0, INF, {1: -1.0, 2: 1.0})


def test_add_rows_moves_constants_into_bounds(solver: Solver) -> None:
    """A constant in an expression shifts the row bounds rather than the coefficients."""
    x = solver.add_variables(1)

    add_rows(solver, x + 2.0 == 5.0)

    assert _row(solver, 0) == (3.0, 3.0, {0: 1.0})


def test_add_rows_raises_and_adds_nothing_when_highs_refuses(solver: Solver) -> None:
    """A block HiGHS rejects adds no rows, so it can be retried."""
    solver.add_variables(1)

    with pytest.raises(RuntimeError, match="refused"):
        add_rows(solver, _terms([[0]], [[INF]]) <= 1.0)

    assert solver.getNumRow() == 0


def test_update_rows_replaces_bounds_and_coefficients(solver: Solver) -> None:
    """Updating changes bounds and coefficients, adding and removing terms as needed."""
    x = solver.add_variables(3)
    indices, applied = add_rows(solver, x[0] + x[1] <= 1.0)

    update_rows(solver, indices, applied, x[1] * 2.0 + x[1] * 3.0 + x[0] * 3e-10 + x[2] <= 4.0)

    assert _row(solver, 0) == (-INF, 4.0, {1: 5.0, 2: 1.0})


def test_change_bounds_frees_rows(solver: Solver) -> None:
    """Rows given unbounded bounds stay in the LP without binding."""
    x = solver.add_variables(1)
    indices, applied = add_rows(solver, x <= 1.0)

    updated = change_bounds(solver, indices, applied, -INF, INF)

    assert _row(solver, 0) == (-INF, INF, {0: 1.0})
    assert updated.is_free


@pytest.mark.parametrize(
    ("make_rows", "expected_calls"),
    [
        pytest.param(lambda a, b: a + b * 2.0 <= 3.0, [], id="unchanged"),
        pytest.param(lambda a, b: a * 0.5 + a * 0.5 + b * 2.0 <= 3.0, [], id="unchanged_after_summing"),
        pytest.param(
            lambda a, b: a + b * 2.0 <= 4.0,
            [call.changeRowsBounds(1, [0], [-INF], [4.0])],
            id="bounds_only",
        ),
        pytest.param(lambda a, b: a + b * 5.0 <= 3.0, [call.changeCoeff(0, 1, 5.0)], id="one_coefficient"),
        pytest.param(lambda a, _b: a <= 3.0, [call.changeCoeff(0, 1, 0.0)], id="removed_term"),
    ],
)
def test_update_rows_writes_only_changed_values(
    solver: Solver,
    make_rows: object,
    expected_calls: list[object],
) -> None:
    """Only bounds and coefficients that differ from the applied rows reach the solver."""
    x = solver.add_variables(2)
    a, b = x[0], x[1]
    indices, applied = add_rows(solver, a + b * 2.0 <= 3.0)
    spy = MagicMock(wraps=solver)

    update_rows(spy, indices, applied, make_rows(a, b))  # type: ignore[operator]

    calls = [
        call.changeRowsBounds(c.args[0], c.args[1].tolist(), c.args[2].tolist(), c.args[3].tolist())
        if c[0] == "changeRowsBounds"
        else c
        for c in spy.mock_calls
    ]
    assert calls == expected_calls
