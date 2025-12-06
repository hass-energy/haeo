"""Graph visualization for HAEO network topology.

This module creates network topology diagrams showing elements and connections
with current and maximum power flows.
"""

import logging
import math
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
import matplotlib.pyplot as plt
import networkx as nx

from custom_components.haeo.elements import ELEMENT_TYPE_CONNECTION

_LOGGER = logging.getLogger(__name__)


def _format_power_label(current_kw: float, min_kw: float, max_kw: float) -> str:
    """Format power label for display with min/max range."""
    return "".join(
        [
            f"{f'{min_kw:.1f} < ' if math.isfinite(min_kw) else ''}",
            f"{current_kw:.1f}kW",
            f"{f' < {max_kw:.1f}' if math.isfinite(max_kw) else ''}",
        ]
    )


def _get_connection_power_flows(
    connection_name: str, forecast_data: dict[str, Any], connection_config: dict[str, Any]
) -> tuple[float, float, float]:
    """Get the power flow and bounds for a connection."""
    # Get data from forecast_data if available
    connection_data = forecast_data.get(connection_name, {})

    # Get the forward and reverse power flows defaulting to 0.0 if not available
    fwd = connection_data.get("connection_flow_forward", [[0, 0.0]])[0][1]
    rev = connection_data.get("connection_flow_reverse", [[0, 0.0]])[0][1]

    # Get max power from config, default to inf if not available
    max_fwd = connection_config.get("max_power_source_target", float("inf"))
    max_rev = connection_config.get("max_power_target_source", float("inf"))

    return fwd - rev, -max_rev, max_fwd


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

    # Create directed graph
    graph: nx.DiGraph[str] = nx.DiGraph()

    # Get participants from config
    participants = config.get("participants", {})

    # Color map for element types
    color_map = {
        "battery": "#98df8a",  # Light green
        "photovoltaics": "#ffbb78",  # Light orange
        "grid": "#aec7e8",  # Light blue
        "load": "#d3d3d3",  # Light gray
        "node": "#f0f0f0",  # Very light gray
    }

    # First pass: add all non-connection elements as nodes
    for name, element_config in participants.items():
        element_type = element_config.get("element_type", "")

        if element_type != ELEMENT_TYPE_CONNECTION:
            fillcolor = color_map.get(element_type, "lightgray")
            graph.add_node(name, color=fillcolor, element_type=element_type)

    # Second pass: add connections as edges
    for name, element_config in participants.items():
        element_type = element_config.get("element_type", "")

        if element_type == ELEMENT_TYPE_CONNECTION:
            source = element_config.get("source")
            target = element_config.get("target")

            # Get power flows for both directions
            (net_flow, min_flow, max_flow) = _get_connection_power_flows(name, forecast_data, element_config)
            label = _format_power_label(net_flow, min_flow, max_flow)
            graph.add_edge(source, target, label=label)

    # Use spectral layout for deterministic positioning
    pos = nx.spectral_layout(graph)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_title(title, fontsize=14, pad=20)

    # Draw nodes with type-specific colors
    for node in graph.nodes():
        node_color = graph.nodes[node].get("color", "lightgray")
        element_type = graph.nodes[node].get("element_type", "")

        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=[node],
            node_color=node_color,
            node_size=3000,
            node_shape="o",
            edgecolors="black",
            linewidths=1.5,
            ax=ax,
        )

        # Draw node label with element name and type
        label_text = f"{node}\n({element_type})"
        nx.draw_networkx_labels(graph, pos, labels={node: label_text}, font_size=10, font_family="sans-serif", ax=ax)

    # Draw edges with arrows
    nx.draw_networkx_edges(
        graph,
        pos,
        edge_color="#666666",
        arrows=True,
        arrowsize=25,
        arrowstyle="->",
        width=2.5,
        node_size=3000,
        min_source_margin=15,
        min_target_margin=15,
        ax=ax,
    )

    # Draw edge labels on curved edges
    edge_labels = nx.get_edge_attributes(graph, "label")
    nx.draw_networkx_edge_labels(
        graph,
        pos,
        edge_labels=edge_labels,
        font_size=8,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "none", "alpha": 0.8},
        font_color="#333333",
        ax=ax,
    )

    # Remove axis
    ax.axis("off")
    plt.tight_layout()

    # Save the graph
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as SVG
    plt.savefig(output_path, format="svg", bbox_inches="tight", dpi=300)
    _LOGGER.info("Graph visualization saved to %s", output_path)

    # Optionally save as PNG
    if generate_png:
        png_path = str(output_path).replace(".svg", ".png")
        plt.savefig(png_path, format="png", bbox_inches="tight", dpi=300)
        _LOGGER.info("Graph visualization saved to %s", png_path)

    plt.close(fig)
