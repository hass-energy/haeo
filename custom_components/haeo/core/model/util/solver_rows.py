"""Add and update HiGHS constraint rows from linear expressions."""

from typing import Final

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression

# HiGHS drops matrix coefficients smaller than its small_matrix_value option
# (default 1e-9) and reports a warning. From highspy 1.15 that warning raises
# out of addConstr after the row has already been added, so terms this small are
# removed before a row reaches the solver. HiGHS would discard them anyway.
SMALL_MATRIX_VALUE: Final = 1e-9


FREE_ROW_BOUNDS: Final = (float("-inf"), float("inf"))


def row_expression(expr: highs_linear_expression) -> highs_linear_expression:
    """Return the expression with repeated variables summed and negligible terms removed.

    An expression without bounds becomes a free row: it is in the LP but does not
    bind, so a constraint that does not currently apply keeps its rows.
    """
    simplified = expr.simplify()
    keep = [i for i, val in enumerate(simplified.vals) if abs(val) >= SMALL_MATRIX_VALUE]
    simplified.idxs = [simplified.idxs[i] for i in keep]
    simplified.vals = [simplified.vals[i] for i in keep]
    if simplified.bounds is None:
        simplified.bounds = FREE_ROW_BOUNDS
    return simplified


def is_free_row(expr: highs_linear_expression) -> bool:
    """Return whether a row expression has no bounds and so does not bind."""
    return expr.bounds is None or tuple(expr.bounds) == FREE_ROW_BOUNDS


def add_row(solver: Highs, expr: highs_linear_expression) -> highs_cons:
    """Add a constraint row for the expression.

    highspy raises after adding the row when HiGHS returns any non-OK status,
    and unlike addConstrs it does not roll back, so the row is removed again
    before the error propagates and a later retry does not add a duplicate.
    """
    rows_before = solver.numConstrs
    try:
        return solver.addConstr(row_expression(expr))
    except Exception:
        added = list(range(rows_before, solver.numConstrs))
        solver.deleteRows(len(added), added)
        raise


def add_rows(solver: Highs, exprs: list[highs_linear_expression]) -> list[highs_cons]:
    """Add a constraint row for each expression."""
    return solver.addConstrs([row_expression(expr) for expr in exprs])


def _row_coefficients(expr: highs_linear_expression) -> dict[int, float]:
    """Return the expression's coefficients as HiGHS stores them.

    Repeated variables are summed and negligible terms removed, matching what
    ``row_expression`` writes when a row is added.
    """
    coeffs: dict[int, float] = {}
    for idx, val in zip(expr.idxs, expr.vals, strict=True):
        coeffs[idx] = coeffs.get(idx, 0.0) + val
    return {idx: val for idx, val in coeffs.items() if abs(val) >= SMALL_MATRIX_VALUE}


def update_row(
    solver: Highs,
    cons: highs_cons,
    applied: highs_linear_expression,
    expr: highs_linear_expression,
) -> None:
    """Change a row from the expression it holds to a new expression.

    The row is diffed against ``applied``, the expression last written to it,
    rather than read back from the solver. HiGHS stores its matrix column-wise,
    so reading a row scans the whole matrix, and every changeCoeff call discards
    the simplex factorization, so only values that differ are written.
    An expression without bounds leaves the row unbounded.
    """
    if applied.bounds != expr.bounds:
        lower, upper = expr.bounds if expr.bounds is not None else (float("-inf"), float("inf"))
        solver.changeRowBounds(cons.index, lower, upper)

    old_coeffs = _row_coefficients(applied)
    new_coeffs = _row_coefficients(expr)
    for var_idx in old_coeffs.keys() | new_coeffs.keys():
        new_val = new_coeffs.get(var_idx, 0.0)
        if old_coeffs.get(var_idx, 0.0) != new_val:
            solver.changeCoeff(cons.index, var_idx, new_val)
