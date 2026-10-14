"""Type stubs for highspy."""

from collections.abc import Callable
from enum import IntEnum
from typing import Literal, overload

import numpy as np
from numpy.typing import NDArray

kHighsInf: float

class HighsStatus(IntEnum):
    kError = -1
    kOk = 0
    kWarning = 1

class ObjSense(IntEnum):
    kMinimize = 0
    kMaximize = 1

class HighsModelStatus(IntEnum):
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
    def __iadd__(self, callback: Callable[[int, str], None]) -> HighsCallback: ...

class HighsSolution:
    @property
    def col_value(self) -> list[float]: ...
    @property
    def col_dual(self) -> list[float]: ...
    @property
    def row_value(self) -> list[float]: ...
    @property
    def row_dual(self) -> list[float]: ...
    @property
    def value_valid(self) -> bool: ...
    @property
    def dual_valid(self) -> bool: ...

class HighsBasisStatus(IntEnum):
    kLower = 0
    kBasic = 1
    kUpper = 2
    kZero = 3
    kNonbasic = 4

class HighsBasis:
    @property
    def col_status(self) -> list[HighsBasisStatus]: ...
    @property
    def row_status(self) -> list[HighsBasisStatus]: ...
    @property
    def valid(self) -> bool: ...

class HighsInfo:
    max_dual_infeasibility: float
    simplex_iteration_count: int

class Highs:
    cbLogging: HighsCallback

    @property
    def numVariables(self) -> int: ...
    @property
    def numConstrs(self) -> int: ...
    def __init__(self) -> None: ...
    @overload
    def setOptionValue(self, option: Literal["solver"], value: str) -> None: ...
    @overload
    def setOptionValue(self, option: Literal["presolve", "parallel"], value: str) -> None: ...
    @overload
    def setOptionValue(self, option: Literal["simplex_strategy", "simplex_scale_strategy"], value: int) -> None: ...
    @overload
    def setOptionValue(self, option: Literal["output_flag", "log_to_console"], value: bool) -> None: ...
    @overload
    def setOptionValue(self, option: str, value: bool | int | float | str) -> None: ...
    @overload
    def getOptionValue(self, option: Literal["output_flag", "log_to_console"]) -> tuple[HighsStatus, bool]: ...
    @overload
    def getOptionValue(
        self, option: Literal["simplex_strategy", "simplex_scale_strategy"]
    ) -> tuple[HighsStatus, int]: ...
    @overload
    def getOptionValue(self, option: str) -> tuple[HighsStatus, bool | int | float | str]: ...
    def run(self) -> HighsStatus: ...
    def getModelStatus(self) -> HighsModelStatus: ...
    def modelStatusToString(self, status: HighsModelStatus) -> str: ...
    def getNumRow(self) -> int: ...
    def getNumCol(self) -> int: ...
    def getRow(self, row: int) -> tuple[HighsStatus, float, float, int]: ...
    def getRowEntries(self, row: int) -> tuple[HighsStatus, NDArray[np.int32], NDArray[np.float64]]: ...
    def addCols(
        self,
        num_cols: int,
        costs: NDArray[np.float64],
        lower_bounds: NDArray[np.float64],
        upper_bounds: NDArray[np.float64],
        num_elements: int,
        starts: NDArray[np.int32],
        indices: NDArray[np.int32],
        values: NDArray[np.float64],
    ) -> HighsStatus: ...
    def addRows(
        self,
        num_rows: int,
        lower_bounds: NDArray[np.float64],
        upper_bounds: NDArray[np.float64],
        num_elements: int,
        starts: NDArray[np.int32],
        indices: NDArray[np.int32],
        values: NDArray[np.float64],
    ) -> HighsStatus: ...
    def getObjectiveValue(self) -> float: ...
    def getSolution(self) -> HighsSolution: ...
    def allVariableValues(self) -> list[float]: ...
    def changeRowsBounds(
        self,
        num_rows: int,
        rows: NDArray[np.int32],
        lower_bounds: NDArray[np.float64],
        upper_bounds: NDArray[np.float64],
    ) -> HighsStatus: ...
    def changeObjectiveSense(self, sense: ObjSense) -> None: ...
    def changeObjectiveOffset(self, offset: float) -> None: ...
    def changeColCost(self, col: int, cost: float) -> None: ...
    def changeColsCost(
        self,
        num_cols: int,
        cols: NDArray[np.int32],
        costs: NDArray[np.float64],
    ) -> None: ...
    def changeColBounds(self, col: int, lower: float, upper: float) -> None: ...
    def changeCoeff(self, row: int, col: int, value: float) -> None: ...
    def getInfoValue(self, info: str) -> tuple[HighsStatus, int | float]: ...
    def getInfo(self) -> HighsInfo: ...
    def getBasis(self) -> HighsBasis: ...
    def getCols(
        self, num_cols: int, indices: NDArray[np.int32]
    ) -> tuple[HighsStatus, int, NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], int]: ...
    def getRows(
        self, num_rows: int, indices: NDArray[np.int32]
    ) -> tuple[HighsStatus, int, NDArray[np.float64], NDArray[np.float64], int]: ...
    def clearLinearObjectives(self) -> None: ...
    def clearSolver(self) -> HighsStatus: ...
