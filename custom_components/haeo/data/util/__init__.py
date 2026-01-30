"""Utility helpers for HAEO data processing."""

from collections.abc import Sequence
from enum import StrEnum


class InterpolationMode(StrEnum):
    """Interpolation mode for forecast data between timepoints."""

    LINEAR = "linear"
    PREVIOUS = "previous"
    NEXT = "next"
    NEAREST = "nearest"


ForecastSeries = Sequence[tuple[float, float]]
SensorPayload = float | ForecastSeries
