"""Test data types for segment scenarios."""

from collections.abc import Callable, Sequence
from typing import Any, Literal, NotRequired, TypedDict

from highspy import Highs
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.elements.segments import SegmentSpec

type ExpectedValue = Sequence[float] | Sequence[str] | float
type SegmentEndpointFactory = Callable[[Highs, NDArray[np.floating[Any]]], tuple[Element[Any], Element[Any]]]


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
    inputs: SegmentScenarioInputs
    expected_outputs: dict[str, ExpectedValue]
    endpoint_factory: NotRequired[SegmentEndpointFactory]


class SegmentErrorScenario(TypedDict):
    """Scenario describing segment initialization errors."""

    description: str
    factory: type
    spec: SegmentSpec
    periods: NDArray[np.floating[Any]]
    error: type[Exception]
    match: str | None
    endpoint_factory: NotRequired[SegmentEndpointFactory]


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
    mirror_segment_order: NotRequired[bool]
    inputs: ConnectionScenarioInputs
    expected_outputs: dict[str, ExpectedValue]
