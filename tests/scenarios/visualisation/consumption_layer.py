"""Consumption layer plotting for HAEO visualizations."""

import logging
from typing import Any

from .colors import ColorMapper

_LOGGER = logging.getLogger(__name__)


def plot_consumption_layer(
    ax: Any, time_values: list[Any], forecast_data: dict[str, Any], color_mapper: ColorMapper
) -> None:
    """Plot the consumption power layer with dotted pattern.

    Args:
        ax: Matplotlib axes to plot on
        time_values: List of datetime objects for x-axis
        forecast_data: Dictionary containing consumption data
        color_mapper: ColorMapper instance for consistent color assignment

    """
    if not forecast_data["consumption"]:
        return

    # Sort consumption by element type for correct stacking order:
    # loads (bottom), battery charge (middle), grid export (top)
    element_types = forecast_data["element_types"]

    def get_sort_order(label: str) -> int:
        """Get sort order for consumption stacking."""
        element_type = element_types.get(label, "")
        if element_type in ["constant_load", "forecast_load", "load"]:
            return 0  # Loads at bottom
        if element_type == "battery":
            return 1  # Battery charge in middle
        if element_type == "grid":
            return 2  # Grid export at top
        return 3  # Unknown types last

    # Sort the consumption data
    sorted_consumption = sorted(forecast_data["consumption"].items(), key=lambda x: get_sort_order(x[0]))
    sorted_labels = [label for label, _ in sorted_consumption]
    sorted_values = [values for _, values in sorted_consumption]

    consumption_values = sorted_values

    if not consumption_values:
        return

    try:
        # Get colors for each element using the color mapper
        colors = []
        for label in sorted_labels:
            element_type = element_types.get(label, "")
            colors.append(color_mapper.get_color(label, element_type))

        # Create stacked area plot for consumption with hatching
        # Use nearly transparent fill, then add fully opaque colored dots via hatching
        data_arrays = [list(values) for values in consumption_values]
        polys = ax.stackplot(
            time_values,
            data_arrays,
            colors=["none"] * len(colors),  # No fill color - transparent background
            zorder=3,  # Above production
        )

        # Add dot hatching to all polygons in the consumption stackplot
        # The hatch will be drawn with the edgecolor at full opacity
        for poly, color in zip(polys, colors, strict=False):
            poly.set_hatch("...")  # Use dots for all consumption areas
            poly.set_edgecolor(color)  # Fully opaque colored dots
            poly.set_linewidth(0.0)  # No border around the polygon

        # Add thicker dashed edge lines on top of the stacked areas for clarity
        # Calculate cumulative sums for each consumption entity
        cumulative_data = []
        current_sum = [0.0] * len(time_values)
        for values in data_arrays:
            current_sum = [sum(x) for x in zip(current_sum, values, strict=False)]
            cumulative_data.append(current_sum.copy())

        # Plot thicker dashed lines on top of the areas
        for i, cumulative_values in enumerate(cumulative_data):
            ax.plot(
                time_values,
                cumulative_values,
                color=colors[i],
                linewidth=2.5,  # Thicker lines for consumption
                linestyle="--",  # Dashed to distinguish from production
                alpha=0.9,
                zorder=4,  # Above consumption fill
            )
    except Exception:
        _LOGGER.exception("Error creating consumption stackplot")
