"""Type stubs for highspy."""

from collections.abc import Callable, Iterable
from enum import IntEnum
from typing import Any, Literal, overload

import numpy as np
from numpy.typing import NDArray

class HighspyArray(np.ndarray[Any, np.dtype[np.object_]]):
    """HiGHS array type - numpy array subclass containing highs_var objects."""

    def __mul__(self, other: float | NDArray[Any]) -> HighspyArray: ...
    def __rmul__(self, other: float | NDArray[Any]) -> HighspyArray: ...
    def __add__(self, other: HighspyArray | highs_var | highs_linear_expression | float) -> HighspyArray: ...
    def __sub__(self, other: HighspyArray | highs_var | highs_linear_expression | float) -> HighspyArray: ...
    def __le__(self, other: HighspyArray | highs_var | highs_linear_expression | float) -> HighspyArray: ...
    def __ge__(self, other: HighspyArray | highs_var | highs_linear_expression | float) -> HighspyArray: ...
    def __eq__(self, other: object) -> HighspyArray: ...  # type: ignore[override]
    @overload
    def __getitem__(self, key: int) -> highs_var: ...
    @overload
    def __getitem__(self, key: slice | NDArray[Any]) -> HighspyArray: ...

class highs_var:
    """HiGHS variable type."""

    @property
    def index(self) -> int:
        """Return the index of this variable in the solver model."""
        ...
    def __add__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __radd__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __sub__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __rsub__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __neg__(self) -> highs_linear_expression: ...
    def __mul__(self, other: float) -> highs_linear_expression: ...
    def __rmul__(self, other: float) -> highs_linear_expression: ...
    def __le__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __ge__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __eq__(self, other: object) -> highs_linear_expression: ...  # type: ignore[override]

class highs_cons:
    """HiGHS constraint type."""

    @property
    def index(self) -> int:
        """Return the index of this constraint in the solver model."""
        ...

class highs_linear_expression:
    """HiGHS linear expression type."""
    def __init__(self, value: float = ...) -> None: ...
    def __add__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __radd__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __sub__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __rsub__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __neg__(self) -> highs_linear_expression: ...
    def __mul__(self, other: float) -> highs_linear_expression: ...
    def __rmul__(self, other: float) -> highs_linear_expression: ...
    def __le__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __ge__(self, other: highs_var | highs_linear_expression | float) -> highs_linear_expression: ...
    def __eq__(self, other: object) -> highs_linear_expression: ...  # type: ignore[override]

class HighsModelStatus(IntEnum):
    """HiGHS model status enumeration."""

    kNotset = 0
    kLoadError = 1
    kModelError = 2
    kPresolveError = 3
    kSolveError = 4
    kPostsolveError = 5
    kModelEmpty = 6
    kOptimal = 7
    kInfeasible = 8
    kUnboundedOrInfeasible = 9
    kUnbounded = 10
    kObjectiveBound = 11
    kObjectiveTarget = 12
    kTimeLimit = 13
    kIterationLimit = 14
    kUnknown = 15
    kSolutionLimit = 16

class HighsCallback:
    """HiGHS callback type."""
    def __iadd__(self, callback: Callable[[int, str], None]) -> HighsCallback: ...

class Highs:
    """HiGHS solver class."""

    cbLogging: HighsCallback

    def __init__(self) -> None: ...
    def setOptionValue(self, option: str, value: bool | int | float | str) -> None: ...
    def getOptionValue(self, option: str) -> bool | int | float | str: ...
    def addVariable(
        self,
        lb: float = ...,
        ub: float = ...,
        obj: float = ...,
        type: int = ...,
        name: str = ...,
    ) -> highs_var: ...
    @overload
    def addVariables(
        self,
        nvars: int,
        lb: float | list[float] = ...,
        ub: float | list[float] = ...,
        obj: float | list[float] = ...,
        type: int = ...,
        name_prefix: str = ...,
        *,
        out_array: Literal[True],
    ) -> HighspyArray: ...
    @overload
    def addVariables(
        self,
        nvars: int,
        lb: float | list[float] = ...,
        ub: float | list[float] = ...,
        obj: float | list[float] = ...,
        type: int = ...,
        name_prefix: str = ...,
        out_array: Literal[False] = ...,
    ) -> dict[Any, highs_var]: ...
    def addConstr(
        self,
        constraint: highs_linear_expression,
        name: str = ...,
    ) -> highs_cons: ...
    def addConstrs(
        self,
        constraints: Iterable[highs_linear_expression] | HighspyArray,
    ) -> list[highs_cons]: ...
    def minimize(
        self,
        expr: highs_var | highs_linear_expression,
    ) -> None: ...
    def run(self) -> None: ...
    def getModelStatus(self) -> HighsModelStatus: ...
    def modelStatusToString(self, status: HighsModelStatus) -> str: ...
    def getObjectiveValue(self) -> float: ...
    def val(self, var: highs_var | highs_linear_expression) -> float: ...
    def vals(
        self,
        idxs: Iterable[highs_var | highs_linear_expression] | HighspyArray | NDArray[Any],
    ) -> NDArray[np.float64]: ...
    def constrDual(self, cons: highs_cons) -> float: ...
    def constrDuals(
        self,
        cons: Iterable[highs_cons] | NDArray[Any],
    ) -> NDArray[np.float64]: ...
    def changeRowBounds(self, row: int, lower: float, upper: float) -> None:
        """Change bounds for a constraint row.

        Args:
            row: Index of the constraint row
            lower: New lower bound
            upper: New upper bound

        """
        ...
    def changeColCost(self, col: int, cost: float) -> None:
        """Change objective coefficient for a variable column.

        Args:
            col: Index of the variable column
            cost: New objective coefficient

        """
        ...
    def changeColBounds(self, col: int, lower: float, upper: float) -> None:
        """Change bounds for a variable column.

        Args:
            col: Index of the variable column
            lower: New lower bound
            upper: New upper bound

        """
        ...
    @staticmethod
    def qsum(
        items: Iterable[highs_var | highs_linear_expression | float | HighspyArray] | NDArray[np.object_],
    ) -> highs_linear_expression: ...
