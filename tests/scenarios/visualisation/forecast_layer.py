"""Forecast layer plotting for HAEO visualizations."""

from __future__ import annotations

import logging
from typing import Any

from .colors import ColorMapper

_LOGGER = logging.getLogger(__name__)


def plot_forecast_layer(
    ax: Any, time_values: list[Any], forecast_data: dict[str, Any], color_mapper: ColorMapper
) -> None:
    """Plot the forecast/available power layer (bottom layer).

    Args:
        ax: Matplotlib axes to plot on
        time_values: List of datetime objects for x-axis
        forecast_data: Dictionary containing forecast data
        color_mapper: ColorMapper instance for consistent color assignment

    """
    if not forecast_data["available"]:
        return

    available_values = list(forecast_data["available"].values())
    available_labels = list(forecast_data["available"].keys())

    if not available_values:
        return

    try:
        # Get colors for each element using the color mapper
        element_types = forecast_data["element_types"]
        colors = []
        for label in available_labels:
            element_type = element_types.get(label, "")
            colors.append(color_mapper.get_color(label, element_type))

        # Create stacked area plot for available power with very light opacity (no hatching)
        data_arrays = [list(values) for values in available_values]
        ax.stackplot(
            time_values,
            data_arrays,
            colors=colors,
            alpha=0.2,  # Very light opacity for forecast
            zorder=1,  # Bottom layer
        )
    except Exception:
        _LOGGER.exception("Error creating available power stackplot")
