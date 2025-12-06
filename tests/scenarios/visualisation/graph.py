"""Graph visualization for HAEO network topology.

This module creates network topology diagrams showing elements and connections
with current and maximum power flows.
"""

import logging
from pathlib import Path
from typing import Any

from graphviz import Digraph
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _format_power(power_kw: float | None) -> str:
    """Format power value in kW for display.

    Args:
        power_kw: Power value in kW (can be None)

    Returns:
        Formatted string like "5.2kW" or "N/A" if None

    """
    if power_kw is None:
        return "N/A"
    return f"{power_kw:.1f}kW"


def _get_connection_power_flow(
    hass: HomeAssistant, connection_name: str, connection_config: dict[str, Any]
) -> tuple[float | None, float | None]:
    """Get current and max power flow for a connection from sensors and config.

    Args:
        hass: Home Assistant instance
        connection_name: Name of the connection element
        connection_config: Configuration for the connection

    Returns:
        Tuple of (current_power_kw, max_power_kw) or (None, None) if not found

    """
    # Look for power flow sensors for this connection
    # Format: sensor.{connection_name}_power_source_target or power_target_source
    connection_sensors = [
        s
        for s in hass.states.async_all("sensor")
        if s.attributes.get("element_name") == connection_name and s.attributes.get("output_type") == "power_flow"
    ]

    # Get the total power flow (sum of both directions)
    total_current = 0.0
    if connection_sensors:
        for sensor in connection_sensors:
            forecast = sensor.attributes.get("forecast", [])
            if forecast:
                # Use first forecast value as representative current power
                total_current += abs(forecast[0].get("value", 0.0))

    # Get max power from config
    max_power_st = connection_config.get("max_power_source_target")
    max_power_ts = connection_config.get("max_power_target_source")

    # Calculate total max power (sum of both directions if both exist, otherwise take the one that exists)
    max_power = None
    if max_power_st is not None and max_power_ts is not None:
        # Both directions have limits
        max_power = float(max_power_st) + float(max_power_ts)
    elif max_power_st is not None:
        max_power = float(max_power_st)
    elif max_power_ts is not None:
        max_power = float(max_power_ts)

    return total_current if total_current > 0 else None, max_power


async def create_graph_visualization(
    hass: HomeAssistant,
    config: dict[str, Any],
    output_path: str,
    title: str,
) -> None:
    """Create a graph visualization of the network topology.

    Args:
        hass: Home Assistant instance containing sensor data
        config: Scenario configuration with participants
        output_path: Path to save the SVG file
        title: Title for the graph

    """
    # Create a new directed graph with deterministic settings
    dot = Digraph(comment=title, format="svg")

    # Use dot layout engine with fixed seed for deterministic output
    dot.engine = "dot"
    dot.graph_attr.update(
        {
            "rankdir": "LR",  # Left to right layout
            "ranksep": "1.5",  # Space between ranks
            "nodesep": "0.8",  # Space between nodes
            "concentrate": "true",  # Merge edges when possible
            "bgcolor": "white",
            "fontname": "Arial",
            "fontsize": "14",
            "label": title,
            "labelloc": "t",  # Title at top
        }
    )

    dot.node_attr.update(
        {
            "shape": "box",
            "style": "rounded,filled",
            "fillcolor": "lightblue",
            "fontname": "Arial",
            "fontsize": "12",
            "margin": "0.3,0.2",
        }
    )

    dot.edge_attr.update(
        {
            "fontname": "Arial",
            "fontsize": "10",
            "color": "gray30",
        }
    )

    # Track which elements we've added
    added_nodes: set[str] = set()

    # Get participants from config
    participants = config.get("participants", {})

    # First pass: add all non-connection elements as nodes
    for name, element_config in participants.items():
        element_type = element_config.get("element_type", "")

        if element_type == "connection":
            continue

        # Determine node color based on element type
        color_map = {
            "battery": "#98df8a",  # Light green
            "photovoltaics": "#ffbb78",  # Light orange
            "grid": "#aec7e8",  # Light blue
            "load": "#d3d3d3",  # Light gray
            "node": "#f0f0f0",  # Very light gray
        }
        fillcolor = color_map.get(element_type, "lightgray")

        # Create node label with element type
        label = f"{name}\\n({element_type})"

        dot.node(name, label=label, fillcolor=fillcolor)
        added_nodes.add(name)

    # Second pass: add connections as edges
    for name, element_config in participants.items():
        element_type = element_config.get("element_type", "")

        if element_type != "connection":
            continue

        source = element_config.get("source")
        target = element_config.get("target")

        if not source or not target:
            _LOGGER.warning("Connection %s missing source or target", name)
            continue

        if source not in added_nodes or target not in added_nodes:
            _LOGGER.warning("Connection %s references unknown element: %s -> %s", name, source, target)
            continue

        # Get power flow information from Home Assistant sensors and config
        current_power, max_power = _get_connection_power_flow(hass, name, element_config)

        # Create edge label with power information
        current_str = _format_power(current_power)
        max_str = _format_power(max_power)
        edge_label = f"{current_str}/{max_str}"

        # Add edge from source to target
        dot.edge(source, target, label=edge_label)

    # Save the graph
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Render to SVG
    output_file = Path(output_path).with_suffix("")  # Remove .svg suffix
    dot.render(str(output_file), cleanup=True)  # cleanup removes the intermediate .gv file

    _LOGGER.info("Graph visualization saved to %s", output_path)

    # Also save as PNG for easier viewing
    png_path = str(output_path).replace(".svg", ".png")
    dot.format = "png"
    dot.render(str(Path(png_path).with_suffix("")), cleanup=True)
    _LOGGER.info("Graph visualization saved to %s", png_path)
