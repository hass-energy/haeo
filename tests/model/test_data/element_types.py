"""Element type definitions for model test data."""

from collections.abc import Callable, Sequence
from typing import Any, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray


class ExpectedOutput(TypedDict):
    """Expected output data structure."""

    type: str
    unit: str
    values: tuple[float, ...]


class ElementTestCaseInputs(TypedDict):
    """Inputs for element optimization scenario."""

    power: NotRequired[Sequence[float | None]]
    input_cost: NotRequired[NDArray[np.floating[Any]]]
    output_cost: NotRequired[NDArray[np.floating[Any]]]


class ElementTestCase(TypedDict):
    """Structure for element test cases."""

    description: str
    factory: Callable[..., Any]
    data: dict[str, Any]
    inputs: NotRequired[ElementTestCaseInputs]
    expected_outputs: NotRequired[dict[str, ExpectedOutput]]
    expected_error: NotRequired[str]
