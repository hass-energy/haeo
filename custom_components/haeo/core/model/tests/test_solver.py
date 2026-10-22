"""Tests for the solver's cached solution."""

import numpy as np

from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util.solver_rows import add_rows


def test_feasibility_relaxation_replaces_the_cached_solution() -> None:
    """The solution a feasibility relaxation finds is the one read after it, not the solve before."""
    solver = Solver()
    solver.setOptionValue("output_flag", False)
    x = solver.add_variables(1, name="x", upper=10.0)
    add_rows(solver, x >= 6.0)
    add_rows(solver, x <= 4.0)
    solver.run()
    before = solver.column_values().copy()
    solver.row_values()
    solver.row_duals()

    solver.feasibilityRelaxation(1.0, 1.0, 1.0, None, None, None)

    solution = solver.getSolution()
    np.testing.assert_allclose(solver.column_values(), solution.col_value)
    np.testing.assert_allclose(solver.row_values(), solution.row_value)
    np.testing.assert_allclose(solver.row_duals(), solution.row_dual)
    assert not np.allclose(solver.column_values(), before)
