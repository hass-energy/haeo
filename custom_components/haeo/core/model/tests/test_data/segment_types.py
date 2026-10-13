"""Test data types for segment scenarios."""

from collections.abc import Sequence
from typing import TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.elements.segments import SegmentSpec

type ExpectedValue = Sequence[float] | Sequence[str] | float


class SegmentScenarioInputs(TypedDict, total=False):
    """Inputs for segment optimization scenarios."""

    power_in: Sequence[float]
    maximize: dict[str, float]
    minimize_cost: bool


class SegmentScenario(TypedDict):
    """Scenario describing segment behavior."""

    description: str
    factory: type
    spec: SegmentSpec
    periods: NDArray[np.float64]
    inputs: SegmentScenarioInputs
    expected_outputs: dict[str, ExpectedValue]


class ConnectionScenarioInputs(TypedDict, total=False):
    """Inputs for connection scenarios."""

    power_in: Sequence[float]
    maximize: dict[str, float]
    minimize_cost: bool
    updates: Sequence[tuple[str, str, Sequence[float] | NDArray[np.float64]]]


class ConnectionScenario(TypedDict):
    """Scenario describing connection behavior."""

    description: str
    periods: NDArray[np.float64]
    segments: dict[str, SegmentSpec] | None
    inputs: ConnectionScenarioInputs
    expected_outputs: dict[str, ExpectedValue]
