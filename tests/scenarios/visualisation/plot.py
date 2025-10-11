"""Main plotting functions for HAEO optimization visualization."""

import asyncio
from datetime import UTC, datetime, timedelta
import logging
import traceback
from typing import Any

from homeassistant.core import HomeAssistant
from matplotlib import dates, patches
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt

from .colors import ColorMapper, get_element_color
from .consumption_layer import plot_consumption_layer
from .forecast_layer import plot_forecast_layer
from .production_layer import plot_production_layer
from .soc_layer import plot_soc_layer

_LOGGER = logging.getLogger(__name__)


def extract_forecast_data_from_sensors(hass: HomeAssistant) -> dict[str, Any]:
    """Extract forecast data from HAEO sensors for visualization.

    This function collects power data from HAEO sensors, organizing it by production
    and consumption categories for use in optimization result visualizations.

    Args:
        hass: Home Assistant instance to extract sensor data from

    Returns:
        Dictionary with keys:
        - production: Dictionary mapping sensor names to power value lists
        - consumption: Dictionary mapping sensor names to power value lists
        - time_index: List of timestamp strings for the data points

    """
    forecast_data: dict[str, Any] = {
        "production": {},
        "consumption": {},
        "available": {},  # For forecast/available power
        "soc": {},  # For battery state of charge
        "time_index": None,
        # Metadata mapping display names to element types
        "element_types": {},
    }

    # Get all HAEO power and SOC sensors
    try:
        # Use async method since we're likely in the event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in the event loop, use a different approach
            # Get all sensor entities and filter them
            all_sensors = list(hass.states.entity_ids("sensor"))
            power_sensors = [
                entity_id for entity_id in all_sensors if entity_id.startswith("sensor.haeo_") and "_power" in entity_id
            ]
            soc_sensors = [
                entity_id
                for entity_id in all_sensors
                if entity_id.startswith("sensor.haeo_") and "state_of_charge" in entity_id
            ]
        else:
            power_sensors = [
                entity_id
                for entity_id in hass.states.entity_ids()
                if entity_id.startswith("sensor.haeo_") and "_power" in entity_id
            ]
            soc_sensors = [
                entity_id
                for entity_id in hass.states.entity_ids()
                if entity_id.startswith("sensor.haeo_") and "state_of_charge" in entity_id
            ]
    except RuntimeError:
        # Fallback: get all entities and filter
        all_entities = list(hass.states.async_entity_ids())
        power_sensors = [
            entity_id for entity_id in all_entities if entity_id.startswith("sensor.haeo_") and "_power" in entity_id
        ]
        soc_sensors = [
            entity_id
            for entity_id in all_entities
            if entity_id.startswith("sensor.haeo_") and "state_of_charge" in entity_id
        ]

    haeo_sensors = power_sensors
    if not haeo_sensors:
        return forecast_data

    # Extract time index from first sensor with timestamped forecast data
    timestamps = None
    for sensor_name in haeo_sensors:
        sensor = hass.states.get(sensor_name)
        if sensor and "timestamped_forecast" in sensor.attributes:
            timestamped = sensor.attributes["timestamped_forecast"]
            if isinstance(timestamped, list) and timestamped:
                # Extract timestamps from timestamped forecast
                timestamps = [item.get("timestamp") for item in timestamped if "timestamp" in item]
                if timestamps:
                    forecast_data["time_index"] = timestamps
                    break

    if not timestamps:
        # If no forecast data, create a simple time index based on current time
        # This allows visualization of current sensor values
        base_time = datetime.now(UTC)
        # Create 48 hours of 5-minute intervals
        timestamps = []
        for i in range(48 * 12):  # 48 hours * 12 intervals per hour
            timestamps.append((base_time + timedelta(minutes=5 * i)).isoformat())
        forecast_data["time_index"] = timestamps

    # Extract forecast data for each sensor
    for sensor_name in haeo_sensors:
        sensor = hass.states.get(sensor_name)
        if not sensor:
            continue

        # Skip transfer connection sensors
        if "_to_" in sensor_name:
            continue

        # Get element metadata from sensor attributes
        data_source = sensor.attributes.get("data_source", "unknown")
        element_type = sensor.attributes.get("element_type", "unknown")

        if data_source == "unknown" or element_type == "unknown":
            continue

        # Extract forecast values
        sensor_values = []
        if "forecast" in sensor.attributes and isinstance(sensor.attributes["forecast"], list):
            forecast_list = sensor.attributes["forecast"]
            sensor_values = [float(v) if v is not None else 0.0 for v in forecast_list]
        elif "timestamped_forecast" in sensor.attributes:
            timestamped = sensor.attributes["timestamped_forecast"]
            sensor_values = [float(item.get("value", 0.0)) for item in timestamped]
        else:
            # No forecast data available
            continue

        # Clean up sensor name for display
        # First replace underscores with spaces, then remove the suffix
        clean_name = sensor_name.replace("sensor.haeo_", "").replace("_", " ").title()

        # Handle based on element type and data source
        if data_source == "optimized":
            # Optimized power values - split by element type
            if element_type == "photovoltaics":
                # Production source
                production_values = [max(0, v) for v in sensor_values]
                if any(v > 0 for v in production_values):
                    display_name = clean_name.replace(" Power", "")
                    forecast_data["production"][display_name] = production_values
                    forecast_data["element_types"][display_name] = element_type

            elif element_type in ["load", "constant_load", "forecast_load"]:
                # Consumption source
                consumption_values = [abs(v) for v in sensor_values]
                if any(v > 0 for v in consumption_values):
                    display_name = clean_name.replace(" Power", "")
                    forecast_data["consumption"][display_name] = consumption_values
                    forecast_data["element_types"][display_name] = element_type

            elif element_type in ["battery", "grid"]:
                # Bidirectional - split by sign
                production_values = [max(0, v) for v in sensor_values]
                consumption_values = [max(0, -v) for v in sensor_values]

                if any(v > 0 for v in production_values):
                    display_name = "Grid Import" if element_type == "grid" else "Battery Discharge"
                    forecast_data["production"][display_name] = production_values
                    forecast_data["element_types"][display_name] = element_type

                if any(v > 0 for v in consumption_values):
                    display_name = "Grid Export" if element_type == "grid" else "Battery Charge"
                    forecast_data["consumption"][display_name] = consumption_values
                    forecast_data["element_types"][display_name] = element_type

        elif data_source == "forecast":
            # Available power forecast (for photovoltaics)
            available_values = [max(0, v) for v in sensor_values]
            if any(v > 0 for v in available_values):
                display_name = clean_name.replace(" Available Power", "")
                forecast_data["available"][display_name] = available_values
                forecast_data["element_types"][display_name] = element_type

    # Extract SOC data from battery sensors
    for sensor_name in soc_sensors:
        sensor = hass.states.get(sensor_name)
        if not sensor:
            continue

        # Extract SOC values
        soc_values = []
        if "forecast" in sensor.attributes and isinstance(sensor.attributes["forecast"], list):
            forecast_list = sensor.attributes["forecast"]
            soc_values = [float(v) if v is not None else 0.0 for v in forecast_list]
        elif "timestamped_forecast" in sensor.attributes:
            timestamped = sensor.attributes["timestamped_forecast"]
            soc_values = [float(item.get("value", 0.0)) for item in timestamped]
        else:
            # No forecast data available
            continue

        # Clean up sensor name for display
        clean_name = sensor_name.replace("sensor.haeo_", "").replace("_state_of_charge", "").replace("_", " ").title()

        if soc_values:
            forecast_data["soc"][clean_name] = soc_values
            forecast_data["element_types"][clean_name] = "battery"  # SOC is always for batteries

    return forecast_data


def create_simplified_legend(ax: Any, forecast_data: dict[str, Any]) -> None:
    """Create a simplified legend showing only element types with their colors.

    Args:
        ax: Matplotlib axes to add legend to
        forecast_data: Dictionary containing forecast data with element types

    """
    if not plt or not patches or Line2D is None:
        return

    # Collect unique element types that are actually present in the data
    element_types_present = set()

    for element_type in forecast_data["element_types"].values():
        element_types_present.add(element_type)

    # Create legend entries for each element type
    legend_elements: list[Any] = []
    element_labels = {
        "photovoltaics": "Photovoltaics",
        "battery": "Battery",
        "grid": "Grid",
        "load": "Load",
        "constant_load": "Load",
        "forecast_load": "Load",
    }

    # Add unique elements in a logical order
    order = ["photovoltaics", "battery", "grid", "load"]
    seen_labels = set()

    for element_type in order:
        if element_type in element_types_present:
            label = element_labels.get(element_type, element_type.title())
            # Avoid duplicate labels (e.g., different load types all show as "Load")
            if label not in seen_labels:
                seen_labels.add(label)
                color = get_element_color(element_type)
                # Create a patch for the legend
                patch = patches.Patch(facecolor=color, edgecolor=color, alpha=0.6, label=label)
                legend_elements.append(patch)

    # Add Battery SOC if present
    if forecast_data["soc"]:
        battery_color = get_element_color("battery")
        soc_line = Line2D([0], [0], color=battery_color, linewidth=2, label="Battery SOC")
        legend_elements.append(soc_line)

    # Position legend in upper left corner inside the plot
    ax.legend(
        handles=legend_elements,
        loc="upper left",
        fontsize=10,
        framealpha=0.9,
        edgecolor="#cccccc",
    )


def create_stacked_visualization(
    hass: HomeAssistant,
    output_path: str = "scenario_optimization_results.svg",
    title: str = "HAEO Optimization Results",
) -> None:
    """Create visualization of HAEO optimization results with stacked plots.

    Creates a visualization showing:
    - Forecast layer (bottom): Available power with light opacity
    - Production layer: Solid filled areas for power production
    - Consumption layer: Dotted pattern areas for power consumption
    - SOC layer: Line plot on secondary y-axis for battery state of charge

    The visualization helps analyze energy flows and optimization effectiveness over time.

    Args:
        hass: Home Assistant instance containing HAEO sensor data
        output_path: File path where the visualization will be saved
        title: Title to display on the plot

    Raises:
        Prints error messages if data extraction fails

    """
    try:
        # Extract forecast data
        forecast_data = extract_forecast_data_from_sensors(hass)

        if not forecast_data["time_index"]:
            _LOGGER.error("No forecast data found in HAEO sensors")
            return

        # Create time index for x-axis
        timestamps = forecast_data["time_index"]
        # Convert timestamps to datetime objects for better plotting
        time_values = []
        for ts in timestamps:
            try:
                # Handle different timestamp formats
                dt = datetime.fromisoformat(ts)
                time_values.append(dt)
            except (ValueError, TypeError):
                # Fallback: create sequential time points
                base_time = datetime.now(UTC)
                time_values.append(base_time + timedelta(minutes=5 * len(time_values)))

        # Create the plot
        if plt is None:
            _LOGGER.error("ERROR: Matplotlib not available for plotting")
            return

        try:
            # Single plot showing both production and consumption overlaid
            fig, ax = plt.subplots(1, 1, figsize=(16, 9))
        except Exception:
            _LOGGER.exception("Failed to create matplotlib figure")
            return

        # Create color mapper to assign consistent colors to elements
        color_mapper = ColorMapper()

        # Plot layers in order (bottom to top)
        plot_forecast_layer(ax, time_values, forecast_data, color_mapper)
        plot_production_layer(ax, time_values, forecast_data, color_mapper)
        plot_consumption_layer(ax, time_values, forecast_data, color_mapper)
        plot_soc_layer(ax, time_values, forecast_data, color_mapper)

        # Set labels and formatting
        ax.set_title(title, fontsize=14, pad=20)
        ax.set_ylabel("Power (kW)", fontsize=11)
        ax.set_xlabel("Time", fontsize=11)

        # Set y-axis to start from 0 to avoid confusing zero points
        ax.set_ylim(bottom=0)

        # Create simplified legend on the plot
        create_simplified_legend(ax, forecast_data)

        ax.grid(alpha=0.3, linestyle=":", linewidth=0.5)
        ax.tick_params(axis="x", rotation=45, labelsize=9)
        ax.tick_params(axis="y", labelsize=9)
        ax.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))  # type: ignore[no-untyped-call]

        # Adjust layout with more room for rotated x-labels
        plt.subplots_adjust(top=0.95, bottom=0.10, left=0.08, right=0.95)

        try:
            # Save as SVG (vector format for crisp, scalable output)
            plt.savefig(output_path, format="svg", bbox_inches="tight", pad_inches=0.3)
            _LOGGER.info("Visualization saved to %s", output_path)

            # Also save as PNG for easier viewing
            png_path = output_path.replace(".svg", ".png")
            plt.savefig(png_path, format="png", bbox_inches="tight", dpi=150, pad_inches=0.3)
            _LOGGER.info("Visualization saved to %s", png_path)
        except Exception:
            _LOGGER.exception("Error saving visualization to %s", output_path)
        finally:
            plt.close(fig)

    except Exception:
        _LOGGER.exception("Error in create_stacked_visualization")
        traceback.print_exc()


def visualize_scenario_results(
    hass: HomeAssistant,
    scenario_name: str = "scenario",
    output_dir: str = ".",
) -> None:
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
    try:
        # Create stacked area/line plots (SVG format for vector graphics)
        main_plot_path = f"{output_dir}/{scenario_name}_optimization.svg"
        create_stacked_visualization(hass, main_plot_path, f"{scenario_name.title()} Optimization Results")
        _LOGGER.info("Main visualization saved to %s", main_plot_path)

        # Summary plot removed - optimization plot shows all necessary information

    except Exception:
        _LOGGER.exception("Error creating visualizations")
        traceback.print_exc()
