"""State of Charge layer plotting for HAEO visualizations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .colors import get_element_color

if TYPE_CHECKING:
    from .colors import ColorMapper

_LOGGER = logging.getLogger(__name__)


def plot_soc_layer(ax: Any, time_values: list[Any], forecast_data: dict[str, Any], color_mapper: ColorMapper) -> Any:
    """Plot the battery State of Charge on a secondary y-axis.

    Args:
        ax: Matplotlib axes to plot on
        time_values: List of datetime objects for x-axis
        forecast_data: Dictionary containing SOC data
        color_mapper: ColorMapper instance for consistent color assignment

    Returns:
        Secondary axes object (ax2) or None if no SOC data

    """
    if not forecast_data["soc"]:
        return None

    try:
        ax2 = ax.twinx()  # Create secondary y-axis

        # Get colors for each battery using the color mapper
        element_types = forecast_data["element_types"]

        # Use solid lines for SOC with distinct style
        for label, values in forecast_data["soc"].items():
            element_type = element_types.get(label, "battery")
            color = color_mapper.get_color(label, element_type)

            ax2.plot(
                time_values,
                values,
                color=color,
                linewidth=2,
                linestyle="-",
                alpha=0.8,
                zorder=5,  # On top
            )

        # Set SOC axis limits and labels - start from 0
        # Use the primary battery color for the axis label
        battery_color = get_element_color("battery")
        ax2.set_ylabel("State of Charge (%)", fontsize=11, color=battery_color)
        ax2.set_ylim(0, 100)
        ax2.tick_params(axis="y", labelcolor=battery_color, labelsize=9)

    except Exception:
        _LOGGER.exception("Error creating SOC lines")
        return None
    else:
        return ax2
