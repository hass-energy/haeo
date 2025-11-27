"""Main plotting functions for HAEO optimization visualization."""

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
import itertools
import logging
from pathlib import Path
from typing import Any, Final, Literal, Required, TypedDict, cast

from cycler import cycler
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
import matplotlib as mpl
from matplotlib import dates
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import numpy as np

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements import ElementType

from .colors import ColorMapper

# Use non-GUI backend
mpl.use("Agg")

# Fix SVG hash salt for consistent output
mpl.rcParams["svg.hashsalt"] = "42"

_LOGGER = logging.getLogger(__name__)


class ForecastData(TypedDict, total=False):
    """Structure for forecast data extracted from HAEO sensors."""

    element_type: ElementType
    color: Required[str]

    # The various forecasts this element may provide mapping timestamp to value
    production: Sequence[tuple[float, float]]
    consumption: Sequence[tuple[float, float]]
    available: Sequence[tuple[float, float]]
    production_price: Sequence[tuple[float, float]]
    consumption_price: Sequence[tuple[float, float]]
    soc: Sequence[tuple[float, float]]
    shadow_prices: dict[str, Sequence[tuple[float, float]]]


ForecastKey = Literal[
    "production",
    "consumption",
    "available",
    "soc",
    "production_price",
    "consumption_price",
]
STACKED_FORECAST_TYPES: Final = ("production", "consumption", "available")
ACTIVITY_EPSILON: Final = 1e-6


async def extract_forecast_data_from_sensors(hass: HomeAssistant) -> dict[str, ForecastData]:
    """Extract forecast data from HAEO sensors for visualization using type+direction filtering."""

    # Get all the HAEO sensors with forecasts
    haeo_sensors = [
        s
        for s in hass.states.async_all("sensor")
        if {"forecast", "element_name", "element_type", "output_type"} <= s.attributes.keys()
    ]

    # Create color mapper to assign consistent colors to elements
    color_mapper = ColorMapper()

    # Fetch translations for sensor names
    translations = await async_get_translations(hass, hass.config.language, "entity", {DOMAIN})

    # Extract forecasts and names
    forecast_data: dict[str, ForecastData] = {}
    for sensor in haeo_sensors:
        if not sensor.attributes.get("advanced", True):
            element_name = sensor.attributes["element_name"]
            element_type = sensor.attributes["element_type"]
            output_type = sensor.attributes["output_type"]
            output_name = sensor.attributes["output_name"]
            direction = sensor.attributes.get("direction")

            # Get sensor display name from translations (output_name is the translation_key)
            sensor_name = translations[f"component.{DOMAIN}.entity.sensor.{output_name}.name"]

            forecast: Sequence[tuple[float, float]] = sorted(
                (dt.timestamp(), value) for dt, value in sensor.attributes["forecast"].items()
            )

            entry = forecast_data.setdefault(
                element_name,
                {
                    "color": color_mapper.get_color(element_name, element_type),
                    "element_type": element_type,
                },
            )

            # Use type+direction to categorize outputs
            # "+" = adding power to graph (production/supply)
            # "-" = taking power away (consumption)
            if output_type == "power" and direction == "+":
                entry["production"] = forecast
            elif output_type == "power" and direction == "-":
                entry["consumption"] = forecast
            elif output_type == "power_limit" and direction == "+":
                entry["available"] = forecast
            elif output_type == "soc":
                entry["soc"] = forecast
            elif output_type == "price" and direction == "+":
                entry["production_price"] = forecast
            elif output_type == "price" and direction == "-":
                entry["consumption_price"] = forecast
            elif output_type == "shadow_price":
                shadow_prices = entry.setdefault("shadow_prices", {})
                # Use translated sensor name as the key for better display
                shadow_prices[sensor_name] = forecast

    return forecast_data


def _compute_activity_metrics(forecast_data: dict[str, ForecastData]) -> dict[str, tuple[float, int, int]]:
    """Return coverage and transition metrics for stacked plotting order."""

    all_timestamps: set[float] = set()
    for data in forecast_data.values():
        for series_key in STACKED_FORECAST_TYPES:
            if isinstance(series := data.get(series_key), Iterable):
                all_timestamps.update(timestamp for timestamp, _ in series)

    if not all_timestamps:
        return dict.fromkeys(forecast_data, (0.0, 0, 0))

    ordered_timestamps = np.array(sorted(all_timestamps), dtype=float)
    metrics: dict[str, tuple[float, int, int]] = {}

    for name, data in forecast_data.items():
        interpolated: list[np.ndarray] = []
        for series_key in STACKED_FORECAST_TYPES:
            series = data.get(series_key)
            if series is None:
                continue

            series_tuples = cast("Sequence[tuple[float, float]]", series)
            series_array = np.asarray(series_tuples, dtype=float)
            if series_array.size == 0:
                continue

            interpolated.append(
                np.abs(np.interp(ordered_timestamps, series_array[:, 0], series_array[:, 1], left=0.0, right=0.0))
            )

        if not interpolated:
            metrics[name] = (0.0, len(ordered_timestamps), len(ordered_timestamps))
            continue

        combined = interpolated[0] if len(interpolated) == 1 else np.maximum.reduce(interpolated)
        active_mask = combined > ACTIVITY_EPSILON

        coverage = float(active_mask.mean())
        transitions = int(np.count_nonzero(np.diff(active_mask.astype(int))))

        active_indices = np.flatnonzero(active_mask)
        first_active_index = int(active_indices[0]) if active_indices.size else len(ordered_timestamps)

        metrics[name] = (coverage, transitions, first_active_index)

    return metrics


def plot_stacked_layer(
    ax: Any,
    forecast_data: Sequence[tuple[str, Sequence[tuple[float, float]]]],
    facecolors: Iterable[str] | None = None,
    edgecolors: Iterable[str] | None = None,
    hatches: Iterable[str] | None = None,
    **format_args: Any,
) -> None:
    """Plot stacked power forecast data on the given axis.

    Power values represent average power over time intervals (not instantaneous values).
    Uses step='post' to display each value from its timestamp through the full period length.
    For example, a value at t=300 with 300-second periods is displayed from t=300 to t=600.
    """

    # Calculate a common time index from the union of all timestamps
    times = np.array(sorted({dt[0] for (_, data) in forecast_data for dt in data}))

    colors: list[str] = []
    data_arrays: list[np.ndarray] = []
    for color, data in forecast_data:
        d = np.asarray(data, dtype=float)
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
        # Only display where there is activity, or the next value after there is
        # activity to allow the step to drop to zero.
        where = np.greater(values, ACTIVITY_EPSILON)
        where[1:] |= where[:-1]

        ax.fill_between(
            [datetime.fromtimestamp(t, tz=UTC) for t in times],
            b,
            t,
            facecolor=facecolor,
            edgecolor=edgecolor,
            hatch=hatch,
            step="post",
            where=where,
            **format_args,
        )


def plot_price_series(ax: Any, forecast_data: Sequence[tuple[str, str, Sequence[tuple[float, float]]]]) -> None:
    """Plot price forecast outputs as line series on the provided axis.

    Prices represent values over time intervals (like power), displayed with
    steps-post to show each price from its timestamp through the period length.
    """

    for label, color, data in forecast_data:
        values = np.asarray(data, dtype=float)

        times_dt = [datetime.fromtimestamp(t, tz=UTC) for t in values[:, 0]]
        ax.plot(times_dt, values[:, 1], color=color, drawstyle="steps-post", label=label)


def plot_soc(ax: Any, forecast_data: Sequence[tuple[str, Sequence[tuple[float, float]]]]) -> None:
    """Plot state of charge (SOC) data on a secondary y-axis.

    SOC represents instantaneous battery state at time boundaries (fence posts),
    not average values over intervals. Uses linear interpolation between points
    to show continuous state transitions.
    """

    ax_soc = ax.twinx()
    ax_soc.set_ylabel("State of Charge (%)", fontsize=11)
    ax_soc.set_ylim(0, 100)

    for color, data in forecast_data:
        d = np.asarray(data, dtype=float)

        times_dt = [datetime.fromtimestamp(t, tz=UTC) for t in d[:, 0]]
        # Use linear interpolation (default) since SOC is instantaneous state, not step function
        ax_soc.plot(times_dt, d[:, 1], color=color, linestyle="--", linewidth=1.5)

    ax_soc.tick_params(axis="y", labelsize=9)


def get_from_sorted_data(
    sorted_data: Sequence[tuple[str, ForecastData]], key: ForecastKey
) -> list[tuple[str, Sequence[tuple[float, float]]]]:
    """Get the forecast data for a specific key from sorted data."""
    result: list[tuple[str, Sequence[tuple[float, float]]]] = []
    for _, data in sorted_data:
        series = data.get(key)
        if series is None:
            continue

        result.append((data["color"], series))

    return result


def collect_shadow_price_series(
    sorted_data: Sequence[tuple[str, ForecastData]],
) -> list[tuple[str, str, Sequence[tuple[float, float]]]]:
    """Return labelled shadow price series for plotting with matplotlib cycling."""

    series: list[tuple[str, str, Sequence[tuple[float, float]]]] = []

    for element_name, data in sorted_data:
        for sensor_name, values in sorted(data.get("shadow_prices", {}).items()):
            if not values:
                continue

            # Use element name and translated sensor name for the label
            label = f"{element_name} {sensor_name}"
            series.append((label, data["color"], values))

    return series


async def create_stacked_visualization(hass: HomeAssistant, output_path: str, title: str) -> None:
    """Create visualization of HAEO optimization results with stacked plots and price traces."""

    # Extract forecast data
    forecast_data = await extract_forecast_data_from_sensors(hass)
    activity_metrics = _compute_activity_metrics(forecast_data)

    def _availability_priority(item: tuple[str, ForecastData]) -> int:
        """Ensure elements with availability forecasts anchor the stack."""
        return 0 if item[1].get("available") else 1

    # Prioritize series that cover the full horizon with few interruptions so they anchor the stack
    sorted_data = sorted(
        forecast_data.items(),
        key=lambda item: (
            _availability_priority(item),
            -activity_metrics[item[0]][0],
            activity_metrics[item[0]][1],
            activity_metrics[item[0]][2],
            item[0],
        ),
    )

    fig, (ax_power, ax_price) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=(16, 10),
        gridspec_kw={"height_ratios": [3, 1]},
    )

    # Set labels and formatting for the power subplot
    ax_power.set_title(title, fontsize=14, pad=20)
    ax_power.set_ylabel("Power (kW)", fontsize=11)
    ax_power.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))  # type: ignore[no-untyped-call]
    ax_power.grid(alpha=0.3, linestyle=":", linewidth=0.5)
    ax_power.tick_params(axis="x", labelsize=9)
    ax_power.tick_params(axis="y", labelsize=9)

    plot_stacked_layer(ax_power, get_from_sorted_data(sorted_data, "available"), alpha=0.2, zorder=1)
    plot_stacked_layer(ax_power, get_from_sorted_data(sorted_data, "production"), alpha=0.6, zorder=2)
    plot_stacked_layer(
        ax_power,
        get_from_sorted_data(sorted_data, "consumption"),
        facecolors=["none"],
        hatches=["..."],
        zorder=3,
    )

    ax_power.set_ylim(bottom=0)

    # Plot the SOC information on a secondary axis
    plot_soc(ax_power, get_from_sorted_data(sorted_data, "soc"))

    ax_power.tick_params(axis="x", labelbottom=False)
    ax_price.set_xlabel("Time", fontsize=11)
    ax_price.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))  # type: ignore[no-untyped-call]
    ax_price.tick_params(axis="x", rotation=45, labelsize=9)
    production_price_series = get_from_sorted_data(sorted_data, "production_price")
    consumption_price_series = get_from_sorted_data(sorted_data, "consumption_price")

    price_series: list[tuple[str, str, Sequence[tuple[float, float]]]] = [
        (f"{label} production price", color, series)
        for label, (color, series) in zip(
            (label for label, data in sorted_data if "production_price" in data),
            production_price_series,
            strict=True,
        )
    ]
    price_series.extend(
        (
            (f"{label} consumption price", color, series)
            for label, (color, series) in zip(
                (label for label, data in sorted_data if "consumption_price" in data),
                consumption_price_series,
                strict=True,
            )
        )
    )

    plot_price_series(ax_price, price_series)

    # Build legend for energy series using the sorted order
    legend_handles = [
        Patch(facecolor=data["color"], label=label)
        for label, data in sorted_data
        if any(key in data for key in STACKED_FORECAST_TYPES)
    ]
    ax_power.legend(handles=legend_handles, loc="upper left", fontsize=9, framealpha=0.9)

    ax_price.set_ylabel("Price", fontsize=11)
    ax_price.grid(alpha=0.3, linestyle=":", linewidth=0.5)
    ax_price.tick_params(axis="y", labelsize=9)
    ax_price.legend(loc="upper left", fontsize=9, framealpha=0.9)

    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.08, right=0.95, hspace=0.15)

    # Save as SVG
    fig.savefig(output_path, format="svg", bbox_inches="tight", pad_inches=0.3, metadata={"Date": None})
    _LOGGER.info("Visualization saved to %s", output_path)

    # Also save as PNG for easier viewing
    png_path = output_path.replace(".svg", ".png")
    fig.savefig(png_path, format="png", bbox_inches="tight", dpi=150, pad_inches=0.3)
    _LOGGER.info("Visualization saved to %s", png_path)

    plt.close(fig)


async def create_shadow_price_visualization(hass: HomeAssistant, output_path: str, title: str) -> bool:
    """Create a dedicated visualization for shadow price series using matplotlib cycling."""

    forecast_data = await extract_forecast_data_from_sensors(hass)
    sorted_data = sorted(forecast_data.items(), key=lambda item: item[0])
    series = collect_shadow_price_series(sorted_data)

    if not series:
        _LOGGER.info("No shadow price data available; skipping shadow price visualization")
        return False

    fig, ax = plt.subplots(1, 1, figsize=(16, 6))

    ax.set_title(title, fontsize=14, pad=20)
    ax.set_ylabel("Shadow price ($/kWh)", fontsize=11)
    ax.set_xlabel("Time", fontsize=11)
    ax.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))  # type: ignore[no-untyped-call]
    ax.grid(alpha=0.3, linestyle=":", linewidth=0.5)
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.tick_params(axis="y", labelsize=9)

    # Set up property cycling for shadow prices (linestyle + linewidth)
    shadow_price_cycler = cycler(linestyle=["-", "--", "-.", ":"]) * cycler(linewidth=[1.5, 2.0])
    ax.set_prop_cycle(shadow_price_cycler)

    for label, color, data in series:
        values = np.asarray(data, dtype=float)
        times_dt = np.asarray([datetime.fromtimestamp(t, tz=UTC) for t in values[:, 0]], dtype=object)
        ax.plot(
            times_dt,
            values[:, 1],
            color=color,
            drawstyle="steps-post",
            label=label,
        )

    ax.axhline(0.0, color="black", linestyle="--", linewidth=0.8, alpha=0.4)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

    fig.subplots_adjust(top=0.90, bottom=0.18, left=0.08, right=0.95)

    fig.savefig(output_path, format="svg", bbox_inches="tight", pad_inches=0.3)
    _LOGGER.info("Shadow price visualization saved to %s", output_path)

    png_path = output_path.replace(".svg", ".png")
    fig.savefig(png_path, format="png", bbox_inches="tight", dpi=150, pad_inches=0.3)
    _LOGGER.info("Shadow price visualization saved to %s", png_path)

    plt.close(fig)
    return True


async def visualize_scenario_results(hass: HomeAssistant, scenario_name: str, output_dir: Path) -> None:
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
    await create_stacked_visualization(hass, str(main_plot_path), f"{scenario_name.title()} Optimization Results")

    shadow_plot_path = output_dir_path / f"{scenario_name}_shadow_prices.svg"
    await create_shadow_price_visualization(hass, str(shadow_plot_path), f"{scenario_name.title()} Shadow Prices")
