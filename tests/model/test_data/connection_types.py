"""Connection type definitions for model test data."""

from collections.abc import Callable, Sequence
from typing import NotRequired, TypedDict


class ExpectedOutput(TypedDict):
    """Expected output data structure."""

    type: str
    unit: str
    values: tuple[float, ...]


type ExpectedOutputValue = ExpectedOutput | dict[str, "ExpectedOutputValue"]


class ConnectionTestCaseInputs(TypedDict):
    """Inputs for connection optimization scenario."""

    source_power: NotRequired[Sequence[float | None]]
    target_power: NotRequired[Sequence[float | None]]
    source_cost: NotRequired[float]
    target_cost: NotRequired[float]


class ConnectionTestCase(TypedDict):
    """Structure for connection test cases."""

    description: str
    factory: Callable[..., object]
    data: dict[str, object]
    inputs: NotRequired[ConnectionTestCaseInputs]
    expected_outputs: NotRequired[dict[str, ExpectedOutputValue]]
    expected_error: NotRequired[str]
