"""HiGHS solver with array-native variables and cached solution arrays."""

from highspy import Highs, HighsStatus
import numpy as np
from numpy.typing import NDArray

from .linear import INF, LinearArray


class Solver(Highs):
    """HiGHS solver that creates variables as ``LinearArray`` columns and caches its solution.

    Reading a solution vector from HiGHS copies the whole vector, so the column
    values and row duals are read once per solve and shared by every output.
    """

    def __init__(self) -> None:
        """Create the solver with no cached solution."""
        super().__init__()
        self._column_values: NDArray[np.float64] | None = None
        self._row_duals: NDArray[np.float64] | None = None

    def add_variables(
        self,
        count: int,
        *,
        lower: float | NDArray[np.float64] = 0.0,
        upper: float | NDArray[np.float64] = INF,
    ) -> LinearArray:
        """Add ``count`` continuous columns with the given bounds and return them as rows of one term."""
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
            msg = f"HiGHS refused to add {count} variables"
            raise RuntimeError(msg)
        return LinearArray.columns(start, count)

    def run(self) -> HighsStatus:
        """Solve the model, discarding the cached solution of the previous solve."""
        self._column_values = None
        self._row_duals = None
        return super().run()

    def column_values(self) -> NDArray[np.float64]:
        """Return the value of every column in the current solution."""
        if self._column_values is None:
            self._column_values = np.asarray(self.getSolution().col_value, dtype=np.float64)
        return self._column_values

    def row_duals(self) -> NDArray[np.float64]:
        """Return the dual value of every row in the current solution."""
        if self._row_duals is None:
            self._row_duals = np.asarray(self.getSolution().row_dual, dtype=np.float64)
        return self._row_duals


__all__ = ["Solver"]
