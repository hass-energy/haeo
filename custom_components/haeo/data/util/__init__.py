"""Utility helpers for HAEO data processing."""

from collections.abc import Sequence

ForecastSeries = Sequence[tuple[int, float]]
SensorPayload = float | ForecastSeries
