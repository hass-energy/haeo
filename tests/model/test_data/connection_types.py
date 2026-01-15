"""Connection type definitions for model test data."""

from collections.abc import Callable, Sequence
from typing import Any, NotRequired, TypedDict


class ExpectedOutput(TypedDict):
    """Expected output data structure."""

    type: str
    unit: str
    values: tuple[float, ...]


class ConnectionTestCaseInputs(TypedDict):
    """Inputs for connection optimization scenario."""

    source_power: NotRequired[Sequence[float | None]]
    target_power: NotRequired[Sequence[float | None]]
    source_cost: NotRequired[float]
    target_cost: NotRequired[float]


class ConnectionTestCase(TypedDict):
    """Structure for connection test cases."""

    description: str
    factory: Callable[..., Any]
    data: dict[str, Any]
    inputs: NotRequired[ConnectionTestCaseInputs]
    expected_outputs: NotRequired[dict[str, Any]]
    expected_error: NotRequired[str]
