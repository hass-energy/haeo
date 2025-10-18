"""Production layer plotting for HAEO visualizations."""

import logging
from typing import Any

from .colors import ColorMapper

_LOGGER = logging.getLogger(__name__)


def plot_production_layer(
    ax: Any, time_values: list[Any], forecast_data: dict[str, Any], color_mapper: ColorMapper
) -> None:
    """Plot the production power layer.

    Args:
        ax: Matplotlib axes to plot on
        time_values: List of datetime objects for x-axis
        forecast_data: Dictionary containing production data
        color_mapper: ColorMapper instance for consistent color assignment

    """
    if not forecast_data["production"]:
        return

    # Reorder production so sources with forecasts are at the bottom (plotted first)
    # This makes them align visually with their forecast lines
    available_names = set(forecast_data["available"].keys())
    production_dict = forecast_data["production"]

    # Split into forecast-enabled and non-forecast sources
    forecast_enabled = {k: v for k, v in production_dict.items() if k in available_names}
    non_forecast = {k: v for k, v in production_dict.items() if k not in available_names}

    # Combine with forecast-enabled first (bottom of stack)
    ordered_production = {**forecast_enabled, **non_forecast}

    production_values = list(ordered_production.values())

    if not production_values:
        return

    try:
        # Get colors for each element using the color mapper
        element_types = forecast_data["element_types"]
        colors = []
        for label in ordered_production:
            element_type = element_types.get(label, "")
            colors.append(color_mapper.get_color(label, element_type))

        # Create stacked area plot for production sources
        data_arrays = [list(values) for values in production_values]
        ax.stackplot(
            time_values,
            data_arrays,
            colors=colors,
            alpha=0.6,
            zorder=2,  # Above forecast
        )
    except Exception:
        _LOGGER.exception("Error creating production stackplot")
