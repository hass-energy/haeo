"""Element type definitions for model test data."""

from collections.abc import Callable
from typing import Any, NotRequired, TypedDict

from numpy.typing import NDArray


class ExpectedOutput(TypedDict):
    """Expected output data structure."""

    type: str
    unit: str
    values: tuple[float, ...]


class ElementTestCaseInputs(TypedDict):
    """Inputs for element optimization scenario."""

    power: NotRequired[list[float | None]]
    input_cost: NotRequired[float | NDArray[Any]]
    output_cost: NotRequired[float | NDArray[Any]]


class ElementTestCase(TypedDict):
    """Structure for element test cases."""

    description: str
    factory: Callable[..., Any]
    data: dict[str, Any]
    inputs: NotRequired[ElementTestCaseInputs]
    expected_outputs: NotRequired[dict[str, ExpectedOutput]]
    expected_error: NotRequired[str]
