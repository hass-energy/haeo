"""Element type definitions for model test data."""

from collections.abc import Callable, Sequence
from typing import Any, NotRequired, TypedDict


class ExpectedOutput(TypedDict):
    """Expected output data structure."""

    type: str
    unit: str
    values: tuple[float, ...]


class ElementTestCaseInputs(TypedDict):
    """Inputs for element optimization scenario."""

    power: NotRequired[Sequence[float | None]]
    input_cost: NotRequired[float | Sequence[float]]
    output_cost: NotRequired[float | Sequence[float]]


class ElementTestCase(TypedDict):
    """Structure for element test cases."""

    description: str
    factory: Callable[..., Any]
    data: dict[str, Any]
    inputs: NotRequired[ElementTestCaseInputs]
    expected_outputs: NotRequired[dict[str, ExpectedOutput]]
    expected_error: NotRequired[str]
