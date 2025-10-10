"""Visualization utilities for HAEO scenario test results.

This module provides functions to create stacked area and line plots
showing production and consumption values over time for optimization results.
"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
import logging
import traceback
from typing import Any

from homeassistant.core import HomeAssistant

try:
    from matplotlib import dates
    import matplotlib.pyplot as plt

    HAS_VISUALIZATION_DEPS = True
except ImportError:
    HAS_VISUALIZATION_DEPS = False

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
        "production": defaultdict(list),
        "consumption": defaultdict(list),
        "available": defaultdict(list),  # For forecast/available power
        "soc": defaultdict(list),  # For battery state of charge
        "time_index": None,
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
        flow_direction = sensor.attributes.get("flow_direction", "unknown")
        element_type = sensor.attributes.get("element_type", "unknown")

        if flow_direction == "unknown":
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

        # Handle based on flow direction from sensor metadata
        if flow_direction == "production":
            # Simple production source (solar, generator)
            production_values = [max(0, v) for v in sensor_values]
            if any(v > 0 for v in production_values):
                # Remove " Power" suffix if present
                display_name = clean_name.replace(" Power", "")
                forecast_data["production"][display_name] = production_values

        elif flow_direction == "consumption":
            # Simple consumption (loads)
            consumption_values = [abs(v) for v in sensor_values]
            if any(v > 0 for v in consumption_values):
                # Remove " Power" suffix if present
                display_name = clean_name.replace(" Power", "")
                forecast_data["consumption"][display_name] = consumption_values

        elif flow_direction == "bidirectional":
            # Battery or Grid - split into production and consumption based on sign
            production_values = [max(0, v) for v in sensor_values]  # Positive = producing/discharging
            consumption_values = [max(0, -v) for v in sensor_values]  # Negative = consuming/charging

            if any(v > 0 for v in production_values):
                if element_type == "grid":
                    forecast_data["production"]["Grid Import"] = production_values
                else:
                    forecast_data["production"]["Battery Discharge"] = production_values

            if any(v > 0 for v in consumption_values):
                if element_type == "grid":
                    forecast_data["consumption"]["Grid Export"] = consumption_values
                else:
                    forecast_data["consumption"]["Battery Charge"] = consumption_values

        elif flow_direction == "forecast":
            # Available power forecast (for generators)
            available_values = [max(0, v) for v in sensor_values]
            if any(v > 0 for v in available_values):
                # Remove " Available Power" suffix to match the production name
                display_name = clean_name.replace(" Available Power", "")
                forecast_data["available"][display_name] = available_values

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

    return forecast_data


def create_stacked_visualization(
    hass: HomeAssistant,
    output_path: str = "scenario_optimization_results.svg",
    title: str = "HAEO Optimization Results",
) -> None:
    """Create visualization of HAEO optimization results with stacked plots.

    Creates a two-panel visualization showing:
    - Top panel: Stacked area plot of all production sources (solar, generators, batteries)
    - Bottom panel: Stacked line plot of all consumption sources (loads, batteries, grid)

    The visualization helps analyze energy flows and optimization effectiveness over time.

    Args:
        hass: Home Assistant instance containing HAEO sensor data
        output_path: File path where the visualization will be saved
        title: Title to display on the plot

    Raises:
        Prints error messages if visualization dependencies are missing or data extraction fails

    """
    if not HAS_VISUALIZATION_DEPS:
        _LOGGER.error(
            "Visualization dependencies (matplotlib) not available. Please install matplotlib to create visualizations."
        )
        _LOGGER.error("You can install it with: uv add matplotlib --dev")
        return

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
            fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        except Exception:
            _LOGGER.exception("Failed to create matplotlib figure")
            return

        # Plot Production (stacked area with fill) - shows where power comes from
        if forecast_data["production"]:
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
            production_labels = [f"{label}" for label in ordered_production]

            if production_values:
                try:
                    # Assign semantic colors based on element type
                    colors = []
                    for label in production_labels:
                        if "Solar" in label or "Generator" in label:
                            colors.append("#ff7f0e")  # Orange for solar/generators
                        elif "Battery" in label:
                            colors.append("#1f77b4")  # Blue for battery
                        elif "Grid" in label:
                            colors.append("#2ca02c")  # Green for grid
                        else:
                            colors.append("#d62728")  # Red fallback

                    # Create stacked area plot for production sources
                    data_arrays = [list(values) for values in production_values]
                    ax.stackplot(time_values, data_arrays, labels=production_labels, colors=colors, alpha=0.6)  # type: ignore[arg-type]
                except Exception:
                    _LOGGER.exception("Error creating production stackplot")

        # Plot Consumption (stacked lines, no fill) - shows where power goes
        if forecast_data["consumption"]:
            consumption_values = list(forecast_data["consumption"].values())
            consumption_labels = [f"{label} (consumption)" for label in forecast_data["consumption"]]

            if consumption_values:
                try:
                    # Create cumulative sum for stacked line effect
                    data_arrays = [list(values) for values in consumption_values]
                    cumulative_data = []
                    current_sum = [0] * len(time_values)

                    # Calculate cumulative sums for each consumption entity
                    for values in data_arrays:
                        current_sum = [sum(x) for x in zip(current_sum, values, strict=False)]
                        cumulative_data.append(current_sum.copy())

                    # Use semantic colors matching the production colors
                    colors = []
                    for label in forecast_data["consumption"]:
                        if "Battery" in label:
                            colors.append("#1f77b4")  # Blue for battery (matching production)
                        elif "Grid" in label:
                            colors.append("#2ca02c")  # Green for grid (matching production)
                        elif "Load" in label:
                            colors.append("#d62728")  # Red for loads
                        else:
                            colors.append("#7f7f7f")  # Gray fallback

                    # Plot stacked consumption lines (dashed lines, no fill, to show overlap with production)
                    for i, (label, cumulative_values) in enumerate(
                        zip(consumption_labels, cumulative_data, strict=False)
                    ):
                        ax.plot(
                            time_values,  # type: ignore[arg-type]
                            cumulative_values,
                            label=label,
                            color=colors[i],
                            linewidth=2.5,
                            linestyle="--",
                            alpha=1.0,
                        )
                except Exception:
                    _LOGGER.exception("Error creating consumption lines")

        # Plot Available Power (dotted lines, semi-transparent) - shows forecast/capacity
        if forecast_data["available"]:
            available_values = list(forecast_data["available"].values())
            available_labels = [f"{label} (available)" for label in forecast_data["available"]]

            if available_values:
                try:
                    # Match forecast line color to the element type for visual alignment
                    for label, values in zip(available_labels, available_values, strict=False):
                        # Determine color based on element type
                        if "Solar" in label or "Generator" in label:
                            color = "#ff7f0e"  # Orange for solar/generators
                        elif "Battery" in label:
                            color = "#1f77b4"  # Blue for battery
                        elif "Grid" in label:
                            color = "#2ca02c"  # Green for grid
                        else:
                            color = "gray"  # Gray fallback

                        ax.plot(
                            time_values,  # type: ignore[arg-type]
                            values,
                            label=label,
                            color=color,
                            linewidth=1.5,
                            linestyle=":",
                            alpha=0.6,
                        )
                except Exception:
                    _LOGGER.exception("Error creating available power lines")

        # Plot Battery SOC on secondary y-axis (0-100%)
        if forecast_data["soc"]:
            try:
                ax2 = ax.twinx()  # Create secondary y-axis
                soc_values = list(forecast_data["soc"].values())
                soc_labels = [f"{label} SOC" for label in forecast_data["soc"]]

                # Use solid lines for SOC with distinct style
                for label, values in zip(soc_labels, soc_values, strict=False):
                    # Use blue color for battery SOC
                    ax2.plot(
                        time_values,  # type: ignore[arg-type]
                        values,
                        label=label,
                        color="#1f77b4",  # Blue for battery
                        linewidth=2,
                        linestyle="-",
                        alpha=0.8,
                    )

                # Set SOC axis limits and labels
                ax2.set_ylabel("State of Charge (%)", fontsize=10, color="#1f77b4")
                ax2.set_ylim(0, 100)
                ax2.tick_params(axis="y", labelcolor="#1f77b4")

                # Add SOC legend to the right side
                ax2_legend = ax2.legend(loc="upper right", fontsize=8)
                ax2_legend.set_zorder(1000)  # Ensure it's on top
            except Exception:
                _LOGGER.exception("Error creating SOC lines")

        # Set labels and formatting
        ax.set_title(
            f"{title}\nFilled = Production, Dashed = Consumption, Dotted = Available, Solid = SOC",
            fontsize=12,
        )
        ax.set_ylabel("Power (W)", fontsize=10)
        ax.set_xlabel("Time", fontsize=10)
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", rotation=45)
        ax.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))  # type: ignore[no-untyped-call]

        plt.tight_layout()
        try:
            # Save as vector format (SVG) for crisp, scalable output
            plt.savefig(output_path, format="svg", bbox_inches="tight")
            _LOGGER.info("Visualization saved to %s", output_path)
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
