"""Previews of a forecast's shape."""

from typing import Final

import numpy as np

from . import ForecastSeries

PREVIEW_POINTS: Final = 48
"""How many values a preview holds."""


def forecast_preview(series: ForecastSeries, now: float, points: int = PREVIEW_POINTS) -> tuple[float, ...]:
    """Return a forecast's values at evenly spaced times from now to its end, to four significant figures.

    Values between the forecast's points are interpolated linearly, as the
    fuser does. A forecast that has ended, or not yet started, is previewed
    over its whole span, and one with fewer than two points has no preview.
    """
    if len(series) < 2:  # noqa: PLR2004  # a line needs two points
        return ()
    array = np.asarray(series, dtype=np.float64)
    times, values = array[:, 0], array[:, 1]
    start = now if times[0] < now < times[-1] else times[0]
    samples = np.interp(np.linspace(start, times[-1], points), times, values)
    return tuple(float(f"{value:.4g}") for value in samples)
