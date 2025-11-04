"""Main plotting functions for HAEO optimization visualization."""

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
import itertools
import logging
from pathlib import Path
from typing import Any, Literal, Required, TypedDict

from homeassistant.core import HomeAssistant
import matplotlib as mpl
from matplotlib import dates
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import numpy as np

from custom_components.haeo.elements import ElementType

# Use non-GUI backend
mpl.use("Agg")

from custom_components.haeo.model import (
    OUTPUT_NAME_BATTERY_STATE_OF_CHARGE,
    OUTPUT_NAME_POWER_AVAILABLE,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_NAME_POWER_EXPORTED,
    OUTPUT_NAME_POWER_IMPORTED,
    OUTPUT_NAME_POWER_PRODUCED,
)

from .colors import ColorMapper

_LOGGER = logging.getLogger(__name__)


class ForecastData(TypedDict, total=False):
    """Structure for forecast data extracted from HAEO sensors."""

    element_type: ElementType
    color: Required[str]

    # The various forecasts this element may provide mapping timestamp to value
    production: Sequence[tuple[float, float]]
    consumption: Sequence[tuple[float, float]]
    available: Sequence[tuple[float, float]]
    soc: Sequence[tuple[float, float]]


def extract_forecast_data_from_sensors(hass: HomeAssistant) -> dict[str, ForecastData]:
    """Extract forecast data from HAEO sensors for visualization."""

    # Get all the HAEO sensors with forecasts
    haeo_sensors = [
        s
        for s in hass.states.async_all("sensor")
        if {"forecast", "element_name", "element_type"} <= s.attributes.keys()
    ]

    # Create color mapper to assign consistent colors to elements
    color_mapper = ColorMapper()

    # Extract forecasts and names
    forecast_data: dict[str, ForecastData] = {}
    for sensor in haeo_sensors:
        device_name = sensor.attributes["element_name"]
        forecast: Sequence[tuple[float, float]] = sorted(
            (datetime.fromisoformat(dt).timestamp(), value) for dt, value in sensor.attributes["forecast"].items()
        )

        v = forecast_data.setdefault(
            device_name, {"color": color_mapper.get_color(device_name, sensor.attributes["element_type"])}
        )
        if sensor.attributes.get("output_name") in (OUTPUT_NAME_POWER_PRODUCED, OUTPUT_NAME_POWER_IMPORTED):
            v["production"] = forecast
        elif sensor.attributes.get("output_name") in (OUTPUT_NAME_POWER_CONSUMED, OUTPUT_NAME_POWER_EXPORTED):
            v["consumption"] = forecast
        elif sensor.attributes.get("output_name") in (OUTPUT_NAME_POWER_AVAILABLE,):
            v["available"] = forecast
        elif sensor.attributes.get("output_name") == OUTPUT_NAME_BATTERY_STATE_OF_CHARGE:
            v["soc"] = forecast

    # Filter out the sensors without any relevant forecast data
    return {
        k: v
        for k, v in forecast_data.items()
        if any(key in v for key in ("production", "consumption", "available", "soc"))
    }



def plot_stacked_layer(
    ax: Any,
    forecast_data: Sequence[tuple[str, Sequence[tuple[float, float]]]],
    facecolors: Iterable[str] | None = None,
    edgecolors: Iterable[str] | None = None,
    hatches: Iterable[str] | None = None,
    **format_args: Any,
) -> None:
    """Plot a stacked layer of forecast data on the given axis."""

    if not forecast_data:
        return

    # Calculate a common time index from the union of all timestamps
    times = np.array(sorted({dt[0] for (_, data) in forecast_data for dt in data}))

    if times.size == 0:
        return

    # Convert Unix timestamps to datetime objects for matplotlib
    times_dt = [datetime.fromtimestamp(t, tz=UTC) for t in times]

    colors: list[str] = []
    data_arrays: list[np.ndarray] = []
    for color, data in forecast_data:
        if not data:
            continue

        d = np.asarray(data, dtype=float)
        if d.size == 0:
            continue

        colors.append(color)
        data_arrays.append(np.interp(times, d[:, 0], d[:, 1], left=0.0, right=0.0))

    if not data_arrays:
        return

    y = np.vstack(data_arrays)

    cumulative = np.cumsum(y, axis=0)
    baseline = np.vstack([np.zeros(times.size, dtype=float), cumulative[:-1]])
    top = cumulative

    facecolors = itertools.cycle(list(facecolors if facecolors is not None else colors))
    edgecolors = itertools.cycle(list(edgecolors if edgecolors is not None else colors))
    hatches = itertools.cycle(list(hatches if hatches is not None else [""]))

    for values, b, t, facecolor, edgecolor, hatch in zip(
        y, baseline, top, facecolors, edgecolors, hatches, strict=False
    ):
        ax.fill_between(
            times_dt,
            b,
            t,
            facecolor=facecolor,
            edgecolor=edgecolor,
            hatch=hatch,
            interpolate=True,
            where=np.greater(values, 0.0),
            **format_args,
        )


def plot_soc(ax: Any, forecast_data: Sequence[tuple[str, Sequence[tuple[float, float]]]]) -> None:
    """Plot the state of charge (SOC) data on a secondary y-axis."""
    if not forecast_data:
        return

    ax_soc = ax.twinx()
    ax_soc.set_ylabel("State of Charge (%)", fontsize=11)
    ax_soc.set_ylim(0, 100)

    for color, data in forecast_data:
        d = np.asarray(data, dtype=float)

        times_dt = [datetime.fromtimestamp(t, tz=UTC) for t in d[:, 0]]
        ax_soc.plot(times_dt, d[:, 1], color=color, linestyle="--", linewidth=1.5)

    ax_soc.tick_params(axis="y", labelsize=9)


def get_from_sorted_data(
    sorted_data: Sequence[tuple[str, ForecastData]], key: ForecastKey
) -> list[tuple[str, Sequence[tuple[float, float]]]]:
    """Get the forecast data for a specific key from sorted data."""
    result: list[tuple[str, Sequence[tuple[float, float]]]] = []
    for _, data in sorted_data:
        if key == "production":
            series = data.get("production")
        elif key == "consumption":
            series = data.get("consumption")
        elif key == "available":
            series = data.get("available")
        else:
            series = data.get("soc")

        if not series:
            continue

        result.append((data["color"], series))

    return result


def create_stacked_visualization(hass: HomeAssistant, output_path: str, title: str) -> None:
    """Create visualization of HAEO optimization results with stacked plots."""

    # Extract forecast data
    forecast_data = extract_forecast_data_from_sensors(hass)

    # Order the data so that sensors with available come first to ensure that they are plotted at the bottom
    # Then order them so that the sensors with the most "non zero" values come first then finally order by name
    sorted_data = sorted(forecast_data.items(), key=lambda item: (item[1].get("available") is None, item[0]))

    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(16, 9))

    # Set labels and formatting
    ax.set_title(title, fontsize=14, pad=20)
    ax.set_ylabel("Power (kW)", fontsize=11)
    ax.set_xlabel("Time", fontsize=11)
    ax.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))  # type: ignore[no-untyped-call]

    ax.grid(alpha=0.3, linestyle=":", linewidth=0.5)
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.tick_params(axis="y", labelsize=9)
    # Adjust layout with more room for rotated x-labels
    fig.subplots_adjust(top=0.95, bottom=0.10, left=0.08, right=0.95)

    plot_stacked_layer(ax, get_from_sorted_data(sorted_data, "available"), alpha=0.2, zorder=1)
    plot_stacked_layer(ax, get_from_sorted_data(sorted_data, "production"), alpha=0.6, zorder=2)
    plot_stacked_layer(
        ax, get_from_sorted_data(sorted_data, "consumption"), facecolors=["none"], hatch=["..."], zorder=3
    )

    ax.set_ylim(bottom=0)

    # Plot the SOC information
    plot_soc(fig, get_from_sorted_data(sorted_data, "soc"))

    # Build legend from forecast_data (each element already has name and color)
    ax.legend(
        handles=[Patch(facecolor=data["color"], label=label) for label, data in forecast_data.items()],
        loc="upper left",
        fontsize=9,
        framealpha=0.9,
    )

    # Save as SVG
    fig.savefig(output_path, format="svg", bbox_inches="tight", pad_inches=0.3)
    _LOGGER.info("Visualization saved to %s", output_path)

    # Also save as PNG for easier viewing
    png_path = output_path.replace(".svg", ".png")
    fig.savefig(png_path, format="png", bbox_inches="tight", dpi=150, pad_inches=0.3)
    _LOGGER.info("Visualization saved to %s", png_path)

    plt.close(fig)


def visualize_scenario_results(hass: HomeAssistant, scenario_name: str, output_dir: Path) -> None:
    """Create comprehensive visualizations for HAEO scenario test results.

    Creates both detailed optimization results visualization and summary metrics
    for a given scenario test. Files are saved with the scenario name prefix.

    Args:
        hass: Home Assistant instance containing HAEO sensor data
        scenario_name: Name identifier for the scenario (used in output filenames)
        output_dir: Directory path where visualization files will be saved

    Raises:
        Prints error messages if visualization creation fails

    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Create stacked area/line plots (SVG format for vector graphics)
    main_plot_path = output_dir_path / f"{scenario_name}_optimization.svg"
    create_stacked_visualization(hass, str(main_plot_path), f"{scenario_name.title()} Optimization Results")
