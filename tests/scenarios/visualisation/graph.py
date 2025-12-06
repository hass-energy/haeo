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


def _format_power_label(current_kw: float | None, max_kw: float | None) -> str:
    """Format power label for display."""
    if current_kw is None or current_kw == 0:
        return ""

    if max_kw is None:
        return f"{current_kw:.1f}kW"

    return f"{current_kw:.1f}kW/{max_kw:.1f}kW"


def _get_connection_power_flows(
    connection_name: str, forecast_data: dict[str, Any], connection_config: dict[str, Any]
) -> tuple[tuple[float | None, float | None], tuple[float | None, float | None]]:
    """Get power flows for both directions of a connection.

    Returns:
        Tuple of ((source_to_target_power, source_to_target_max), (target_to_source_power, target_to_source_max))

    """
    # Get data from forecast_data if available
    connection_data = forecast_data.get(connection_name, {})

    # Get current power from forecasts
    st_power = None
    ts_power = None

    production = connection_data.get("production")
    consumption = connection_data.get("consumption")

    if production:
        # Production means power flowing in positive direction
        st_power = production[0][1] if production else None

    if consumption:
        # Consumption means power flowing in negative direction
        ts_power = abs(consumption[0][1]) if consumption else None

    # Get max power from config
    st_max = connection_config.get("max_power_source_target")
    ts_max = connection_config.get("max_power_target_source")

    st_max = float(st_max) if st_max is not None else None
    ts_max = float(ts_max) if ts_max is not None else None

    return (st_power, st_max), (ts_power, ts_max)


async def create_graph_visualization(
    hass: HomeAssistant,
    config: dict[str, Any],
    forecast_data: dict[str, Any],
    output_path: str,
    title: str,
    *,
    generate_png: bool = True,
) -> None:
    """Create a graph visualization of the network topology."""

    # Create a new directed graph with deterministic settings
    dot = Digraph(comment=title, format="svg")

    # Use dot layout engine with fixed seed for deterministic output
    dot.engine = "dot"
    dot.graph_attr.update(
        {
            "rankdir": "LR",  # Left to right layout
            "ranksep": "1.5",  # Space between ranks
            "nodesep": "0.8",  # Space between nodes
            "concentrate": "false",  # Don't merge edges - show both directions
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

    # Second pass: add connections as edges (separate edge for each direction)
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

        # Get power flows for both directions
        (st_power, st_max), (ts_power, ts_max) = _get_connection_power_flows(name, forecast_data, element_config)

        # Add edge from source to target if there's power flow or max limit
        st_label = _format_power_label(st_power, st_max)
        if st_label:
            dot.edge(source, target, label=st_label)

        # Add edge from target to source if there's power flow or max limit
        ts_label = _format_power_label(ts_power, ts_max)
        if ts_label:
            dot.edge(target, source, label=ts_label)

    # Save the graph
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Render to SVG
    output_file = Path(output_path).with_suffix("")  # Remove .svg suffix
    dot.render(str(output_file), cleanup=True)  # cleanup removes the intermediate .gv file

    _LOGGER.info("Graph visualization saved to %s", output_path)

    # Optionally save as PNG for easier viewing
    if generate_png:
        png_path = str(output_path).replace(".svg", ".png")
        dot.format = "png"
        dot.render(str(Path(png_path).with_suffix("")), cleanup=True)
        _LOGGER.info("Graph visualization saved to %s", png_path)
