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
    over its whole span. Points that are not finite are left out, and a
    forecast with fewer than two other points has no preview.
    """
    array = np.asarray(series, dtype=np.float64).reshape(-1, 2)
    array = array[np.isfinite(array).all(axis=1)]
    if len(array) < 2:  # noqa: PLR2004  # a line needs two points
        return ()
    times, values = array[:, 0], array[:, 1]
    start = now if times[0] < now < times[-1] else times[0]
    samples = np.interp(np.linspace(start, times[-1], points), times, values)
    return tuple(float(f"{value:.4g}") for value in samples)
