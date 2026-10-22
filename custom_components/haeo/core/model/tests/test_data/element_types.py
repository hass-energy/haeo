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
    """Inputs for element optimization scenario.

    ``power`` fixes the power flowing into the element in each period, where
    given. ``max_power`` and ``min_power`` bound it instead, a negative power
    being power flowing out. Each kWh in costs ``input_cost`` and each kWh out
    costs ``output_cost``.
    """

    power: NotRequired[Sequence[float | None]]
    input_cost: NotRequired[NDArray[np.float64] | float]
    output_cost: NotRequired[NDArray[np.float64] | float]
    max_power: NotRequired[Sequence[float]]
    min_power: NotRequired[Sequence[float]]


class ElementTestCase(TypedDict):
    """Structure for element test cases."""

    description: str
    factory: Callable[..., Any]
    data: dict[str, Any]
    inputs: NotRequired[ElementTestCaseInputs]
    expected_outputs: NotRequired[dict[str, ExpectedOutput]]
    expected_cost: NotRequired[float]
