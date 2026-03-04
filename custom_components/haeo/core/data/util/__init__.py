"""Utility helpers for HAEO data processing."""

from collections.abc import Sequence

ForecastSeries = Sequence[tuple[float, float]]
SensorPayload = float | ForecastSeries
