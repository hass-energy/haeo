"""Add and update HiGHS constraint rows from linear expressions."""

from typing import Final

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression

# HiGHS drops matrix coefficients smaller than its small_matrix_value option
# (default 1e-9) and reports a warning. From highspy 1.15 that warning raises
# out of addConstr after the row has already been added, so terms this small are
# removed before a row reaches the solver. HiGHS would discard them anyway.
SMALL_MATRIX_VALUE: Final = 1e-9


def row_expression(expr: highs_linear_expression) -> highs_linear_expression:
    """Return the expression with repeated variables summed and negligible terms removed."""
    simplified = expr.simplify()
    keep = [i for i, val in enumerate(simplified.vals) if abs(val) >= SMALL_MATRIX_VALUE]
    simplified.idxs = [simplified.idxs[i] for i in keep]
    simplified.vals = [simplified.vals[i] for i in keep]
    return simplified


def add_row(solver: Highs, expr: highs_linear_expression) -> highs_cons:
    """Add a constraint row for the expression."""
    return solver.addConstr(row_expression(expr))


def add_rows(solver: Highs, exprs: list[highs_linear_expression]) -> list[highs_cons]:
    """Add a constraint row for each expression."""
    return solver.addConstrs([row_expression(expr) for expr in exprs])


def _row_coefficients(expr: highs_linear_expression) -> dict[int, float]:
    """Return the expression's coefficients with repeated variables summed and negligible terms removed."""
    coeffs: dict[int, float] = {}
    for idx, val in zip(expr.idxs, expr.vals, strict=True):
        coeffs[idx] = coeffs.get(idx, 0.0) + val
    return {idx: val for idx, val in coeffs.items() if abs(val) >= SMALL_MATRIX_VALUE}


def update_row(solver: Highs, cons: highs_cons, expr: highs_linear_expression) -> None:
    """Change an existing row's bounds and coefficients to match the expression.

    Rows are updated in place on every optimization, so this compares
    coefficients directly instead of building a simplified expression.
    """
    old_row = solver.getExpr(cons)
    old_bounds = old_row.bounds
    new_bounds = expr.bounds

    if old_bounds != new_bounds:
        if new_bounds is not None:
            solver.changeRowBounds(cons.index, new_bounds[0], new_bounds[1])
        elif old_bounds is not None:
            solver.changeRowBounds(cons.index, float("-inf"), float("inf"))

    old_coeffs = dict(zip(old_row.idxs, old_row.vals, strict=True))
    new_coeffs = _row_coefficients(expr)
    for var_idx in set(old_coeffs) | set(new_coeffs):
        old_val = old_coeffs.get(var_idx, 0.0)
        new_val = new_coeffs.get(var_idx, 0.0)
        if old_val != new_val:
            solver.changeCoeff(cons.index, var_idx, new_val)
