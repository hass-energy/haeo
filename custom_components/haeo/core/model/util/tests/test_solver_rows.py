"""Tests for the solver row helpers."""

from highspy import Highs
import pytest

from custom_components.haeo.core.model.util.solver_rows import add_row, add_rows, row_expression, update_row


@pytest.fixture
def solver() -> Highs:
    """Return a quiet solver."""
    h = Highs()
    h.setOptionValue("output_flag", False)
    return h


def _coefficients(solver: Highs, cons: object) -> dict[int, float]:
    row = solver.getExpr(cons)  # type: ignore[arg-type]
    return {int(idx): float(val) for idx, val in zip(row.idxs, row.vals, strict=True)}


def test_row_expression_sums_repeated_variables_and_drops_negligible_terms(solver: Highs) -> None:
    """Repeated variables are summed and terms below the small matrix value are removed."""
    x = solver.addVariables(3)
    row = row_expression(1.0 * x[0] + 2.0 * x[0] + 3e-10 * x[1] + 4.0 * x[2] + 2 <= 5)

    assert dict(zip(row.idxs, row.vals, strict=True)) == {x[0].index: 3.0, x[2].index: 4.0}
    assert row.bounds == (float("-inf"), 3.0)


def test_add_row_accepts_negligible_coefficients(solver: Highs) -> None:
    """A negligible coefficient does not make highspy reject the row."""
    x = solver.addVariables(2)

    cons = add_row(solver, x[0] + 3e-10 * x[1] <= 1)

    assert solver.numConstrs == 1
    assert _coefficients(solver, cons) == {x[0].index: 1.0}


def test_add_rows_accepts_negligible_coefficients(solver: Highs) -> None:
    """Every row in a batch has its negligible coefficients removed."""
    x = solver.addVariables(2)

    rows = add_rows(solver, [x[0] + 3e-10 * x[1] <= 1, 2e-10 * x[0] + x[1] <= 2])

    assert solver.numConstrs == 2
    assert [_coefficients(solver, cons) for cons in rows] == [{x[0].index: 1.0}, {x[1].index: 1.0}]


def test_update_row_replaces_bounds_and_coefficients(solver: Highs) -> None:
    """Updating a row changes its bounds, sums repeated variables, and zeroes dropped terms."""
    x = solver.addVariables(3)
    cons = add_row(solver, x[0] + x[1] <= 1)

    update_row(solver, cons, 2.0 * x[1] + 3.0 * x[1] + 3e-10 * x[0] + x[2] <= 4)

    assert solver.getExpr(cons).bounds == (float("-inf"), 4.0)
    assert {idx: val for idx, val in _coefficients(solver, cons).items() if val != 0.0} == {
        x[1].index: 5.0,
        x[2].index: 1.0,
    }


def test_update_row_removes_bounds(solver: Highs) -> None:
    """An expression without bounds leaves the row unbounded."""
    x = solver.addVariables(1)
    cons = add_row(solver, x[0] <= 1)

    update_row(solver, cons, 1.0 * x[0])

    assert solver.getExpr(cons).bounds == (float("-inf"), float("inf"))
