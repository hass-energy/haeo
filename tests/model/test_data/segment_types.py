"""Test data types for segment scenarios."""

from collections.abc import Sequence
from datetime import tzinfo
from typing import Any, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.elements.segments import SegmentSpec

type ExpectedValue = Sequence[float] | Sequence[str] | float


class SegmentScenarioInputs(TypedDict, total=False):
    """Inputs for segment optimization scenarios."""

    power_in_st: Sequence[float]
    power_in_ts: Sequence[float]
    maximize: dict[Literal["power_in_st", "power_in_ts"], float]
    minimize_cost: bool


class SegmentScenario(TypedDict):
    """Scenario describing segment behavior."""

    description: str
    factory: type
    spec: SegmentSpec
    periods: NDArray[np.floating[Any]]
    period_start_times: NotRequired[NDArray[np.floating[Any]]]
    period_start_timezone: NotRequired[tzinfo]
    inputs: SegmentScenarioInputs
    expected_outputs: dict[str, ExpectedValue]


class ConnectionScenarioInputs(TypedDict, total=False):
    """Inputs for connection scenarios."""

    power_source_target: Sequence[float]
    power_target_source: Sequence[float]
    maximize: dict[Literal["power_source_target", "power_target_source"], float]
    minimize_cost: bool
    updates: Sequence[tuple[str, str, Sequence[float] | NDArray[np.floating[Any]]]]


class ConnectionScenario(TypedDict):
    """Scenario describing connection behavior."""

    description: str
    periods: NDArray[np.floating[Any]]
    segments: dict[str, SegmentSpec] | None
    inputs: ConnectionScenarioInputs
    expected_outputs: dict[str, ExpectedValue]
