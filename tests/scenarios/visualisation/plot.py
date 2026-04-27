"""Main plotting functions for HAEO optimization visualization."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Final, Literal, Required, TypedDict

from cycler import cycler
from dateutil.parser import isoparse
import matplotlib as mpl
from matplotlib import dates
import matplotlib.pyplot as plt
import numpy as np

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.elements import ElementType

from .colors import ColorMapper
from .graph import create_graph_visualization
from .svg_normalize import normalize_svg_file_clip_paths

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
    connection_flow_forward: Sequence[tuple[float, float]]
    connection_flow_reverse: Sequence[tuple[float, float]]


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


def extract_forecast_data(output_sensors: Mapping[str, Mapping[str, Any]]) -> dict[str, ForecastData]:
    """Extract forecast data from output sensors dict for visualization."""
    # Create color mapper to assign consistent colors to elements
    color_mapper = ColorMapper()

    # Extract forecasts and names
    forecast_data: dict[str, ForecastData] = {}

    for sensor_data in output_sensors.values():
        attrs = sensor_data.get("attributes", {})

        # Must have element_name and element_type
        if "element_name" not in attrs or "element_type" not in attrs:
            continue

        # Skip advanced sensors
        if attrs.get("advanced", False):
            continue

        forecast_attr = attrs.get("forecast")
        if not forecast_attr:
            continue

        element_name = attrs["element_name"]
        element_type = attrs["element_type"]

        # Parse forecast: list of {"time": ISO string or datetime, "value": number}
        forecast: Sequence[tuple[float, float]] = sorted(_parse_forecast_items(forecast_attr))

        entry = forecast_data.setdefault(
            element_name,
            {
                "color": color_mapper.get_color(element_name, element_type),
                "element_type": element_type,
            },
        )

        # Both output sensors and input entities use output_name and field_type
        output_type = attrs.get("field_type")
        output_name = attrs.get("output_name", "")
        direction = attrs.get("direction")
        config_mode = attrs.get("config_mode")

        # Handle input entities first (have config_mode) - they take priority
        if config_mode is not None:
            # Skip constant inputs (all values the same) - they're not interesting to plot
            values = [v for _, v in forecast]
            if values and all(v == values[0] for v in values):
                continue

            # Input entities now have direction from schema field metadata
            if output_type == OutputType.POWER:
                # Solar power inputs are forecasts of available power (limits)
                if element_type == ElementType.SOLAR:
                    entry["available"] = forecast
                elif direction == "+":
                    # Power production inputs → available power
                    entry["available"] = forecast
                elif direction == "-":
                    # Power consumption inputs (load forecast) → consumption
                    entry["consumption"] = forecast
                else:
                    # No direction specified, default to available for power inputs
                    entry["available"] = forecast
            elif output_type == OutputType.PRICE:
                if direction == "+":
                    entry["production_price"] = forecast
                elif direction == "-":
                    entry["consumption_price"] = forecast
                else:
                    # No direction specified, default to consumption price
                    entry["consumption_price"] = forecast
            continue

        # Handle output sensors (have output_type but no config_mode)
        if output_type is not None:
            # SOC doesn't need direction
            if output_type == OutputType.STATE_OF_CHARGE:
                entry["soc"] = forecast
                continue

            # Power-related types need direction
            if direction is not None:
                # Use type+direction to categorize outputs
                # "+" = adding power to graph (production/supply)
                # "-" = taking power away (consumption)
                if output_type == OutputType.POWER and direction == "+":
                    entry["production"] = forecast
                elif output_type == OutputType.POWER and direction == "-":
                    entry["consumption"] = forecast
                elif output_type == OutputType.POWER_LIMIT and direction == "+" and element_type == ElementType.SOLAR:
                    entry["available"] = forecast
                elif output_type == OutputType.PRICE and direction == "+":
                    entry["production_price"] = forecast
                elif output_type == OutputType.PRICE and direction == "-":
                    entry["consumption_price"] = forecast
                elif output_type == OutputType.SHADOW_PRICE:
                    shadow_prices = entry.setdefault("shadow_prices", {})
                    # Use output_name as the key (matches translation_key)
                    shadow_prices[output_name] = forecast
                continue

    return forecast_data


def _parse_forecast_items(forecast_attr: list[Mapping[str, Any]]) -> list[tuple[float, float]]:
    """Parse forecast items handling both datetime objects and ISO strings.

    Args:
        forecast_attr: List of forecast items with 'time' (datetime or ISO string) and 'value'.

    Returns:
        List of (timestamp, value) tuples.

    """
    result: list[tuple[float, float]] = []
    for item in forecast_attr:
        time_val = item["time"]
        # Handle both datetime objects (from hass.states) and ISO strings (from outputs.json)
        timestamp = isoparse(time_val).timestamp() if isinstance(time_val, str) else time_val.timestamp()
        result.append((timestamp, float(item["value"])))
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


def create_shadow_price_visualization(
    output_sensors: Mapping[str, Mapping[str, Any]], output_path: str, title: str
) -> None:
    """Create a dedicated visualization for shadow price series using matplotlib cycling."""

    forecast_data = extract_forecast_data(output_sensors)
    sorted_data = sorted(forecast_data.items(), key=lambda item: item[0])
    series = collect_shadow_price_series(sorted_data)

    if not series:
        _LOGGER.info("No shadow price data available; skipping shadow price visualization")
        return

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
    normalize_svg_file_clip_paths(Path(output_path))
    _LOGGER.info("Shadow price visualization saved to %s", output_path)

    png_path = output_path.replace(".svg", ".png")
    fig.savefig(png_path, format="png", bbox_inches="tight", dpi=150, pad_inches=0.3)
    _LOGGER.info("Shadow price visualization saved to %s", png_path)

    plt.close(fig)
    return


def visualize_scenario_results(
    output_sensors: Mapping[str, Mapping[str, Any]],
    scenario_name: str,
    output_dir: Path,
    network: Network,
) -> None:
    """Create comprehensive visualizations for HAEO scenario test results.

    Renders the forecast card as the main optimization chart, creates shadow
    price visualization (matplotlib), and a network topology graph. Files are saved with the scenario name prefix.

    Args:
        output_sensors: Dict mapping entity_id to sensor state dict (from get_output_sensors
            or loaded from outputs.json).
        scenario_name: Name identifier for the scenario (used in output filenames)
        output_dir: Directory path where visualization files will be saved
        network: Network object containing model elements for graph visualization

    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Create optimization chart using the forecast card renderer
    main_plot_path = output_dir_path / f"{scenario_name}_optimization.svg"
    create_card_visualization(output_sensors, str(main_plot_path))

    shadow_plot_path = output_dir_path / f"{scenario_name}_shadow_prices.svg"
    create_shadow_price_visualization(output_sensors, str(shadow_plot_path), f"{scenario_name.title()} Shadow Prices")

    # Create network topology graph visualization
    graph_plot_path = output_dir_path / f"{scenario_name}_network_topology.svg"
    create_graph_visualization(network, str(graph_plot_path), f"{scenario_name.title()} Network Topology")


def create_card_visualization(
    output_sensors: Mapping[str, Mapping[str, Any]],
    output_path: str,
) -> None:
    """Render the HAEO forecast card as SVG via the bundled card component.

    Calls the Node.js export script which uses JSDOM to render the card
    headlessly. Falls back to matplotlib if Node.js is not available.

    Raises:
        RuntimeError: If the export script is missing, Node.js is not
            installed, or the card fails to render.

    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    script = repo_root / "frontend" / "haeo-forecast-card" / "scripts" / "export-scenario-svg.mjs"

    if not script.exists():
        msg = f"Card export script not found: {script}"
        raise RuntimeError(msg)

    # Write outputs to a temp file for the node script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(output_sensors, f, default=str)
        temp_path = f.name

    try:
        result = subprocess.run(  # noqa: S603 — trusted repo-local script, no user input
            ["node", str(script), temp_path, output_path],  # noqa: S607 — node is a well-known executable
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(script.parent.parent),
            check=False,
        )
        if result.returncode != 0:
            msg = f"Card export failed (exit {result.returncode}): {result.stderr}"
            raise RuntimeError(msg)
    except FileNotFoundError as e:
        msg = f"Node.js not found — required for card visualization: {e}"
        raise RuntimeError(msg) from e
    except subprocess.TimeoutExpired as e:
        msg = f"Card export timed out after {e.timeout}s"
        raise RuntimeError(msg) from e
    finally:
        Path(temp_path).unlink(missing_ok=True)
