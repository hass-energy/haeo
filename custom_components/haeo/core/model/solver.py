"""HiGHS solver with array-native variables and cached solution arrays."""

from bisect import bisect_right
from typing import override

from highspy import Highs, HighsSolution, HighsStatus
import numpy as np
from numpy.typing import NDArray

from .linear import INF, LinearArray, Rows


class Solver(Highs):
    """HiGHS solver that creates variables as ``LinearArray`` columns and caches its solution.

    Reading the solution from HiGHS copies every vector in it, so it is read
    once per solve, and the column values, row values and row duals taken from
    it are shared by every output.

    Every group of variables is named, and ``describe`` prints expressions and
    rows with those names. The names are kept here rather than in HiGHS, which
    would take a call per column.
    """

    def __init__(self) -> None:
        """Create the solver with no cached solution."""
        super().__init__()
        self._solution: HighsSolution | None = None
        self._column_values: NDArray[np.float64] | None = None
        self._row_values: NDArray[np.float64] | None = None
        self._row_duals: NDArray[np.float64] | None = None
        # First column and name of each group of variables, in column order
        self._group_starts: list[int] = []
        self._group_names: list[str] = []

    def add_variables(
        self,
        count: int,
        *,
        name: str,
        lower: float | NDArray[np.float64] = 0.0,
        upper: float | NDArray[np.float64] = INF,
    ) -> LinearArray:
        """Add ``count`` continuous columns named ``name[0]`` onwards, and return them as rows of one term."""
        start = self.getNumCol()
        status = self.addCols(
            count,
            np.zeros(count),
            np.broadcast_to(np.asarray(lower, dtype=np.float64), (count,)),
            np.broadcast_to(np.asarray(upper, dtype=np.float64), (count,)),
            0,
            np.zeros(0, dtype=np.int32),
            np.zeros(0, dtype=np.int32),
            np.zeros(0),
        )
        if status == HighsStatus.kError:
            msg = f"HiGHS refused to add {count} variables for {name}"
            raise RuntimeError(msg)
        self._group_starts.append(start)
        self._group_names.append(name)
        return LinearArray.columns(start, count)

    def column_name(self, column: int) -> str:
        """Return a column's name, such as ``Battery.energy_in[3]``."""
        group = bisect_right(self._group_starts, column) - 1
        return f"{self._group_names[group]}[{column - self._group_starts[group]}]"

    def describe(self, item: LinearArray | Rows) -> str:
        """Print an expression or rows with each column shown by name."""
        return item.format(self.column_name)

    def _discard_solution(self) -> None:
        """Forget the cached solution, so the next read takes the one HiGHS now holds."""
        self._solution = None
        self._column_values = None
        self._row_values = None
        self._row_duals = None

    def _cached_solution(self) -> HighsSolution:
        """Return the current solution, reading it from HiGHS once."""
        if self._solution is None:
            self._solution = self.getSolution()
        return self._solution

    def run(self) -> HighsStatus:
        """Solve the model, discarding the cached solution of the previous solve."""
        self._discard_solution()
        return super().run()

    @override
    def feasibilityRelaxation(
        self,
        global_lower_penalty: float,
        global_upper_penalty: float,
        global_rhs_penalty: float,
        local_lower_penalty: NDArray[np.float64] | None = None,
        local_upper_penalty: NDArray[np.float64] | None = None,
        local_rhs_penalty: NDArray[np.float64] | None = None,
    ) -> HighsStatus:
        """Find the smallest weighted violation that makes the model feasible, discarding the cached solution.

        The relaxation replaces HiGHS's solution with its own, so the previous solve's is no longer current.
        """
        self._discard_solution()
        return super().feasibilityRelaxation(
            global_lower_penalty,
            global_upper_penalty,
            global_rhs_penalty,
            local_lower_penalty,
            local_upper_penalty,
            local_rhs_penalty,
        )

    def column_values(self) -> NDArray[np.float64]:
        """Return the value of every column in the current solution."""
        if self._column_values is None:
            self._column_values = np.asarray(self._cached_solution().col_value, dtype=np.float64)
        return self._column_values

    def row_values(self) -> NDArray[np.float64]:
        """Return the value of every row in the current solution."""
        if self._row_values is None:
            self._row_values = np.asarray(self._cached_solution().row_value, dtype=np.float64)
        return self._row_values

    def row_duals(self) -> NDArray[np.float64]:
        """Return the dual value of every row in the current solution."""
        if self._row_duals is None:
            self._row_duals = np.asarray(self._cached_solution().row_dual, dtype=np.float64)
        return self._row_duals


__all__ = ["Solver"]
